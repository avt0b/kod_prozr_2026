from uuid import UUID

from src.core.utils.text import format_rub
from src.modules.risk.application.dto.risk_dto import GraphDTO
from src.modules.risk.application.interfaces.appeals_source import AppealsSourceInterface
from src.modules.risk.application.interfaces.counterparties_source import (
    CounterpartiesSourceInterface,
)
from src.modules.risk.application.interfaces.officials_source import OfficialsSourceInterface
from src.modules.risk.application.interfaces.risk_repository import RiskRepositoryInterface
from src.modules.risk.domain.enums import EdgeType, NodeType, RuleCode
from src.modules.risk.domain.exceptions import InvalidGraphDepthError, RiskSubjectNotFoundError
from src.modules.risk.domain.facts import KINSHIP_LABELS, ROLE_LABELS
from src.modules.risk.domain.graph import ConnectionsGraph, GraphEdge, GraphNode

MAX_DEPTH = 3
MAX_NODES = 300
MAX_CONTRACTS = 100

CATEGORY_LABELS = {
    "bribe": "взятка",
    "conflict_of_interest": "конфликт интересов",
    "procurement": "закупки",
    "abuse_of_power": "превышение полномочий",
    "other": "другое",
}


class GetOfficialGraphUseCase:
    """Граф связей служащего (GET /officials/{id}/graph?depth=N), строится обходом в ширину.

    depth считает «прыжки» между людьми, компаниями, органами и обращениями:
      1 — родственники, свои компании и места работы, органы, обращения;
      2 — + компании родственников, совладельцы компаний и т.д.
    Контракты — не отдельный прыжок: в конце к компаниям графа добавляются их контракты
    с органами, уже попавшими в граф. Так при depth=2 видна полная цепочка R01:
    служащий -> родственник -> компания -> контракт -> орган служащего.
    """

    def __init__(
        self,
        officials: OfficialsSourceInterface,
        counterparties: CounterpartiesSourceInterface,
        appeals: AppealsSourceInterface,
        repository: RiskRepositoryInterface,
    ) -> None:
        self._officials = officials
        self._counterparties = counterparties
        self._appeals = appeals
        self._repository = repository

    async def execute(self, person_id: UUID, depth: int = 2) -> GraphDTO:
        if not 1 <= depth <= MAX_DEPTH:
            raise InvalidGraphDepthError(depth, MAX_DEPTH)
        found = await self._officials.officials([person_id])
        if not found:
            raise RiskSubjectNotFoundError(person_id)
        root = found[0]

        graph = ConnectionsGraph(root_id=person_id, max_nodes=MAX_NODES)
        graph.add_node(GraphNode(root.person.id, NodeType.PERSON, root.person.full_name))
        frontier_persons: set[UUID] = {person_id}
        frontier_companies: set[UUID] = set()

        for _ in range(depth):
            new_persons, new_companies = await self._expand_persons(graph, frontier_persons)
            more_persons = await self._expand_companies(graph, frontier_companies)
            frontier_persons = new_persons | more_persons
            frontier_companies = new_companies
            if graph.truncated or not (frontier_persons or frontier_companies):
                break

        await self._attach_flag_evidence(graph, person_id)
        await self._attach_contracts(graph)
        scores = await self._repository.get_scores(graph.ids_of(NodeType.PERSON))
        graph.set_risk({s.person_id: s.score for s in scores})
        return GraphDTO.from_graph(graph)

    async def _expand_persons(
        self, graph: ConnectionsGraph, person_ids: set[UUID]
    ) -> tuple[set[UUID], set[UUID]]:
        new_persons: set[UUID] = set()
        new_companies: set[UUID] = set()
        if not person_ids:
            return new_persons, new_companies
        ids = list(person_ids)

        for link in await self._officials.relatives(ids):
            if graph.add_node(
                GraphNode(link.relative.id, NodeType.PERSON, link.relative.full_name)
            ):
                new_persons.add(link.relative.id)
            graph.add_edge(
                GraphEdge(
                    link.person_id,
                    link.relative.id,
                    EdgeType.KINSHIP,
                    KINSHIP_LABELS.get(link.kind, "родственник"),
                )
            )

        officials = await self._officials.officials(ids)
        for official in officials:
            for appointment in official.appointments:
                graph.add_node(
                    GraphNode(appointment.organ_id, NodeType.ORGAN, appointment.organ_name)
                )
                graph.add_edge(
                    GraphEdge(
                        official.person.id,
                        appointment.organ_id,
                        EdgeType.APPOINTMENT,
                        appointment.position_title,
                    )
                )

        roles = await self._counterparties.roles_for_persons(ids)
        employment_links = [(o.person.id, e) for o in officials for e in o.employments]
        company_ids = list(
            {r.company_id for r in roles} | {e.company_id for _, e in employment_links}
        )
        companies = {c.id: c for c in await self._counterparties.companies(company_ids)}
        for role in roles:
            company = companies.get(role.company_id)
            if company is None:
                continue
            if graph.add_node(GraphNode(company.id, NodeType.COMPANY, company.name)):
                new_companies.add(company.id)
            share = f", {role.share:g}%" if role.share is not None else ""
            edge_type = EdgeType.DIRECTOR if role.role == "director" else EdgeType.FOUNDER
            graph.add_edge(
                GraphEdge(
                    role.person_id,
                    company.id,
                    edge_type,
                    ROLE_LABELS.get(role.role, role.role) + share,
                )
            )
        for owner_id, employment in employment_links:
            company = companies.get(employment.company_id)
            if company is None:
                continue
            if graph.add_node(GraphNode(company.id, NodeType.COMPANY, company.name)):
                new_companies.add(company.id)
            graph.add_edge(GraphEdge(owner_id, company.id, EdgeType.EMPLOYMENT, "место работы"))

        for mention in await self._appeals.mentions(ids):
            label = (
                f"Обращение от {mention.received_at:%d.%m.%Y}"
                f" ({CATEGORY_LABELS.get(mention.category or '', 'без категории')})"
            )
            graph.add_node(GraphNode(mention.appeal_id, NodeType.APPEAL, label))
            graph.add_edge(
                GraphEdge(mention.appeal_id, mention.person_id, EdgeType.MENTIONS, "упоминает")
            )
        return new_persons, new_companies

    async def _expand_companies(self, graph: ConnectionsGraph, company_ids: set[UUID]) -> set[UUID]:
        if not company_ids:
            return set()
        roles = await self._counterparties.roles_for_companies(list(company_ids))
        persons = {
            p.id: p for p in await self._officials.persons(list({r.person_id for r in roles}))
        }
        new_persons: set[UUID] = set()
        for role in roles:
            person = persons.get(role.person_id)
            if person is None:
                continue
            if graph.add_node(GraphNode(person.id, NodeType.PERSON, person.full_name)):
                new_persons.add(person.id)
            edge_type = EdgeType.DIRECTOR if role.role == "director" else EdgeType.FOUNDER
            graph.add_edge(
                GraphEdge(
                    person.id, role.company_id, edge_type, ROLE_LABELS.get(role.role, role.role)
                )
            )
        return new_persons

    async def _attach_flag_evidence(self, graph: ConnectionsGraph, person_id: UUID) -> None:
        """Узлы из evidence флагов служащего всегда есть в графе: фронт подсвечивает цепочку.

        Связь R05 (общий адрес или телефон) в данных не ребро, поэтому добавляем ребро
        shared_contact от человека из цепочки к компании.
        """
        for flag in await self._repository.get_flags([person_id]):
            for node in flag.evidence:
                graph.add_node(GraphNode(node.id, node.type, node.label))
            if flag.rule_code is RuleCode.R05:
                persons = [n for n in flag.evidence if n.type is NodeType.PERSON]
                companies = [n for n in flag.evidence if n.type is NodeType.COMPANY]
                if persons and companies:
                    graph.add_edge(
                        GraphEdge(
                            persons[-1].id,
                            companies[0].id,
                            EdgeType.SHARED_CONTACT,
                            "общий адрес или телефон",
                        )
                    )

    async def _attach_contracts(self, graph: ConnectionsGraph) -> None:
        company_ids = graph.ids_of(NodeType.COMPANY)
        organ_ids = graph.ids_of(NodeType.ORGAN)
        if not company_ids or not organ_ids:
            return
        contracts = await self._counterparties.contracts(
            customer_organ_ids=organ_ids, supplier_company_ids=company_ids, limit=MAX_CONTRACTS
        )
        for contract in contracts:
            label = f"№{contract.reg_number}, {format_rub(contract.amount)}"
            graph.add_node(GraphNode(contract.id, NodeType.CONTRACT, label))
            graph.add_edge(
                GraphEdge(contract.supplier_company_id, contract.id, EdgeType.SUPPLIER, "поставщик")
            )
            graph.add_edge(
                GraphEdge(contract.id, contract.customer_organ_id, EdgeType.CUSTOMER, "заказчик")
            )
