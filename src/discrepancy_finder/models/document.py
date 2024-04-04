from datetime import datetime
from typing import NewType, Optional

from pydantic import BaseModel
from pydantic_mongo import ObjectIdField

DocumentId = NewType('DocumentId', str)


class DocumentRow(BaseModel):
    header: str
    body: list[float]


class Document(BaseModel):
    id: ObjectIdField = None
    document_id: DocumentId
    title: Optional[str]
    header: list[str]
    body: list[DocumentRow]
    footer: Optional[str]
    country_of_creation: Optional[str]
    date_of_creation: Optional[datetime]
