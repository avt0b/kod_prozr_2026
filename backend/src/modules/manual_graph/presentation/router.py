from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.infrastructure.auth import current_user
from src.core.infrastructure.database.models.auth import Role, UserModel
from src.core.infrastructure.dependencies import get_session
from src.modules.manual_graph.application.reference_graph import ReferenceGraph
from src.modules.manual_graph.domain.policy import EDGE_LIMIT, NODE_LIMIT, validate_edge
from src.modules.manual_graph.infrastructure.models import (
    EdgeModel,
    NodeModel,
    ShareModel,
    WorkspaceModel,
)
from src.modules.manual_graph.presentation.dependencies import get_reference_graph

router = APIRouter(prefix="/graph-workspaces", tags=["Analyst graph"])
# Схемы видят только сотрудники: гражданам доступ к рабочему месту закрыт (#70).
STAFF = (Role.ANALYST, Role.ADMIN)
DB = Annotated[AsyncSession, Depends(get_session)]
User = Annotated[UserModel, Depends(current_user)]
Reference = Annotated[ReferenceGraph, Depends(get_reference_graph)]


class TextFields(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    notes: str = Field(default="", max_length=2000)
    source: str = Field(default="", max_length=500)


class CreateWorkspace(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=120)
    official_id: UUID


class CreateNode(TextFields):
    kind: Literal["person", "company", "organ", "contract", "appeal"]
    label: str = Field(min_length=1, max_length=200)


class CreateEdge(TextFields):
    source_id: UUID
    target_id: UUID
    label: str = Field(min_length=1, max_length=160)


class SharesRequest(BaseModel):
    user_ids: list[UUID] = Field(max_length=30)

    @field_validator("user_ids")
    @classmethod
    def unique_users(cls, values: list[UUID]) -> list[UUID]:
        return list(dict.fromkeys(values))


class PersonResponse(BaseModel):
    id: UUID
    username: str


class NodeResponse(CreateNode):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class EdgeResponse(CreateEdge):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class WorkspaceSummary(BaseModel):
    id: UUID
    official_id: UUID
    owner_id: UUID
    owner_name: str
    title: str
    created_at: datetime
    can_edit: bool


class WorkspaceResponse(WorkspaceSummary):
    nodes: list[NodeResponse]
    edges: list[EdgeResponse]
    shared_with: list[PersonResponse]


async def access(
    db: AsyncSession, identifier: UUID, user: UserModel, *, write: bool = False
) -> WorkspaceModel:
    # Readers and writers share the workspace lock so nodes, edges and access
    # are serialized as one consistent snapshot under READ COMMITTED.
    query = (
        select(WorkspaceModel)
        .where(WorkspaceModel.id == identifier)
        .with_for_update(read=not write)
    )
    workspace = (await db.execute(query)).scalar_one_or_none()
    shared = workspace is not None and (await db.get(ShareModel, (identifier, user.id))) is not None
    if workspace is None or (workspace.owner_id != user.id and not shared):
        raise HTTPException(404, "Аналитическая схема не найдена или доступ отозван.")
    if write and workspace.owner_id != user.id:
        raise HTTPException(403, "Изменять схему может только её владелец.")
    return workspace


async def serialize(
    db: AsyncSession, workspace: WorkspaceModel, user: UserModel
) -> WorkspaceResponse:
    owner = await db.get(UserModel, workspace.owner_id)
    nodes = (
        await db.scalars(
            select(NodeModel).where(NodeModel.workspace_id == workspace.id).order_by(NodeModel.id)
        )
    ).all()
    edges = (
        await db.scalars(
            select(EdgeModel).where(EdgeModel.workspace_id == workspace.id).order_by(EdgeModel.id)
        )
    ).all()
    recipients = (
        (
            await db.scalars(
                select(UserModel)
                .join(ShareModel, ShareModel.user_id == UserModel.id)
                .where(ShareModel.workspace_id == workspace.id)
                .order_by(UserModel.username)
            )
        ).all()
        if workspace.owner_id == user.id
        else []
    )
    return WorkspaceResponse(
        id=workspace.id,
        official_id=workspace.official_id,
        owner_id=workspace.owner_id,
        owner_name=owner.username if owner else "Пользователь",
        title=workspace.title,
        created_at=workspace.created_at,
        can_edit=workspace.owner_id == user.id,
        nodes=[NodeResponse.model_validate(node) for node in nodes],
        edges=[EdgeResponse.model_validate(edge) for edge in edges],
        shared_with=[PersonResponse(id=item.id, username=item.username) for item in recipients],
    )


@router.get("/users", response_model=list[PersonResponse])
async def users(
    user: User, db: DB, query: Annotated[str, Query(max_length=64)] = ""
) -> list[PersonResponse]:
    statement = select(UserModel).where(
        UserModel.active.is_(True), UserModel.role.in_(STAFF), UserModel.id != user.id
    )
    if query.strip():
        statement = statement.where(
            UserModel.username.contains(query.strip().lower(), autoescape=True)
        )
    items = (await db.scalars(statement.order_by(UserModel.username).limit(30))).all()
    return [PersonResponse(id=item.id, username=item.username) for item in items]


@router.get("", response_model=list[WorkspaceSummary])
async def workspaces(user: User, db: DB, official_id: UUID | None = None) -> list[WorkspaceSummary]:
    shared = select(ShareModel.workspace_id).where(ShareModel.user_id == user.id)
    statement = (
        select(WorkspaceModel, UserModel.username)
        .join(UserModel, WorkspaceModel.owner_id == UserModel.id)
        .where(or_(WorkspaceModel.owner_id == user.id, WorkspaceModel.id.in_(shared)))
    )
    if official_id:
        statement = statement.where(WorkspaceModel.official_id == official_id)
    rows = (await db.execute(statement.order_by(WorkspaceModel.created_at.desc()).limit(100))).all()
    return [
        WorkspaceSummary(
            id=item.id,
            official_id=item.official_id,
            owner_id=item.owner_id,
            owner_name=name,
            title=item.title,
            created_at=item.created_at,
            can_edit=item.owner_id == user.id,
        )
        for item, name in rows
    ]


@router.post("", response_model=WorkspaceResponse, status_code=201)
async def create_workspace(
    body: CreateWorkspace, user: User, db: DB, reference: Reference
) -> WorkspaceResponse:
    await reference.node_ids(body.official_id)
    workspace = WorkspaceModel(owner_id=user.id, official_id=body.official_id, title=body.title)
    db.add(workspace)
    await db.flush()
    result = await serialize(db, workspace, user)
    await db.commit()
    return result


@router.get("/{identifier}", response_model=WorkspaceResponse)
async def get_workspace(identifier: UUID, user: User, db: DB) -> WorkspaceResponse:
    return await serialize(db, await access(db, identifier, user), user)


@router.delete("/{identifier}", status_code=204)
async def delete_workspace(identifier: UUID, user: User, db: DB) -> None:
    workspace = await access(db, identifier, user, write=True)
    await db.delete(workspace)
    await db.commit()


@router.post("/{identifier}/nodes", response_model=WorkspaceResponse, status_code=201)
async def add_node(identifier: UUID, body: CreateNode, user: User, db: DB) -> WorkspaceResponse:
    workspace = await access(db, identifier, user, write=True)
    count = await db.scalar(
        select(func.count()).select_from(NodeModel).where(NodeModel.workspace_id == identifier)
    )
    if count is not None and count >= NODE_LIMIT:
        raise HTTPException(409, "В схеме уже 50 ручных объектов.")
    db.add(NodeModel(workspace_id=identifier, **body.model_dump()))
    await db.flush()
    result = await serialize(db, workspace, user)
    await db.commit()
    return result


@router.delete("/{identifier}/nodes/{node_id}", response_model=WorkspaceResponse)
async def remove_node(identifier: UUID, node_id: UUID, user: User, db: DB) -> WorkspaceResponse:
    workspace = await access(db, identifier, user, write=True)
    node = await db.get(NodeModel, node_id)
    if node is None or node.workspace_id != identifier:
        raise HTTPException(404, "Ручной объект не найден.")
    await db.execute(
        delete(EdgeModel).where(
            EdgeModel.workspace_id == identifier,
            or_(EdgeModel.source_id == node_id, EdgeModel.target_id == node_id),
        )
    )
    await db.delete(node)
    await db.flush()
    result = await serialize(db, workspace, user)
    await db.commit()
    return result


@router.post("/{identifier}/edges", response_model=WorkspaceResponse, status_code=201)
async def add_edge(
    identifier: UUID, body: CreateEdge, user: User, db: DB, reference: Reference
) -> WorkspaceResponse:
    workspace = await access(db, identifier, user, write=True)
    originals = await reference.node_ids(workspace.official_id)
    manual = set(
        (await db.scalars(select(NodeModel.id).where(NodeModel.workspace_id == identifier))).all()
    )
    validate_edge(body.source_id, body.target_id, originals | manual)
    count = await db.scalar(
        select(func.count()).select_from(EdgeModel).where(EdgeModel.workspace_id == identifier)
    )
    if count is not None and count >= EDGE_LIMIT:
        raise HTTPException(409, "В схеме уже 100 ручных связей.")
    db.add(EdgeModel(workspace_id=identifier, **body.model_dump()))
    await db.flush()
    result = await serialize(db, workspace, user)
    await db.commit()
    return result


@router.delete("/{identifier}/edges/{edge_id}", response_model=WorkspaceResponse)
async def remove_edge(identifier: UUID, edge_id: UUID, user: User, db: DB) -> WorkspaceResponse:
    workspace = await access(db, identifier, user, write=True)
    edge = await db.get(EdgeModel, edge_id)
    if edge is None or edge.workspace_id != identifier:
        raise HTTPException(404, "Ручная связь не найдена.")
    await db.delete(edge)
    await db.flush()
    result = await serialize(db, workspace, user)
    await db.commit()
    return result


@router.put("/{identifier}/shares", response_model=WorkspaceResponse)
async def share_workspace(
    identifier: UUID, body: SharesRequest, user: User, db: DB
) -> WorkspaceResponse:
    workspace = await access(db, identifier, user, write=True)
    recipients = set(body.user_ids) - {user.id}
    existing = set(
        (
            await db.scalars(
                select(UserModel.id).where(
                    UserModel.id.in_(recipients),
                    UserModel.active.is_(True),
                    UserModel.role.in_(STAFF),
                )
            )
        ).all()
    )
    if recipients != existing:
        raise HTTPException(422, "Один из получателей отсутствует, отключён или не сотрудник.")
    await db.execute(delete(ShareModel).where(ShareModel.workspace_id == identifier))
    for recipient in recipients:
        db.add(ShareModel(workspace_id=identifier, user_id=recipient))
    await db.flush()
    result = await serialize(db, workspace, user)
    await db.commit()
    return result
