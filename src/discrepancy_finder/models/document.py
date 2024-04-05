from datetime import datetime
from typing import TypeAlias, Optional

from .base import BaseModel, BaseModelWithObjectId

DocumentId: TypeAlias = str


class DocumentRow(BaseModel):
    header: str
    body: list[float]


class Document(BaseModelWithObjectId):
    document_id: DocumentId
    title: Optional[str]
    header: list[str]
    body: list[DocumentRow]
    footer: Optional[str]
    country_of_creation: Optional[str]
    date_of_creation: Optional[datetime]
