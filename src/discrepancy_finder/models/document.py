from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from pydantic_extra_types.country import CountryShortName
from pydantic_mongo import ObjectIdField


class DocumentRow(BaseModel):
    header: str
    body: list[str]


class Document(BaseModel):
    id: ObjectIdField = None
    document_id: str
    # todo: what should be the placeholders for missing values?
    title: Optional[str]
    header: list[str]
    body: list[DocumentRow]
    footer: Optional[str]
    country_of_creation: Optional[str]
    date_of_creation: Optional[datetime]
