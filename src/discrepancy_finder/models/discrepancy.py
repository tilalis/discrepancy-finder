from typing import TypeAlias

from .base import BaseModelWithObjectId

DiscrepancyLocation: TypeAlias = str
DiscrepancyTypeDescription: TypeAlias = str
DiscrepancyId: TypeAlias = str


class Discrepancy(BaseModelWithObjectId):
    discrepancy_id: DiscrepancyId
    document_id: str
    discrepancy_type: DiscrepancyTypeDescription
    location: DiscrepancyLocation
    details: dict
