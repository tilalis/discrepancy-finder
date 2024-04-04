from pydantic import BaseModel
from pydantic_mongo import ObjectIdField

from typing import NamedTuple
from .discrepancy_location import DiscrepancyLocation
from .discrepancy_types import DiscrepancyType


class Discrepancy(BaseModel):
    id: ObjectIdField = None
    discrepancy_id: str
    document_id: ObjectIdField
    discrepancy_type: DiscrepancyType
    location: DiscrepancyLocation
    details: str
