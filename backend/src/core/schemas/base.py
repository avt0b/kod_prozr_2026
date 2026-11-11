from pydantic import BaseModel, ConfigDict


class APIModel(BaseModel):
    """База для схем ответов: собирается из DTO-датаклассов по атрибутам."""

    model_config = ConfigDict(from_attributes=True)
