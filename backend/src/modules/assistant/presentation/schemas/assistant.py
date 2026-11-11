from pydantic import Field

from src.core.schemas import APIModel, SafeString


class AskRequest(APIModel):
    question: SafeString = Field(min_length=1, max_length=2000)


class SourceResponse(APIModel):
    type: str
    id: str
    label: str


class AskResponse(APIModel):
    answer: str
    sources: list[SourceResponse]
