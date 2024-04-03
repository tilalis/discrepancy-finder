from pydantic import BaseModel
from pydantic_mongo import ObjectIdField

from typing import NamedTuple


class DiscrepancyLocation(NamedTuple):
    row: int
    column: int


class Discrepancy(BaseModel):
    id: ObjectIdField = None
    discrepancy_id: str
    document_id: ObjectIdField
    discrepancy_type: str
    location: DiscrepancyLocation
    details: str
