from typing import NewType

from .base import BaseModelWithObjectId

DiscrepancyLocation = NewType('DiscrepancyLocation', str)
DiscrepancyTypeDescription = NewType('DiscrepancyTypeDescription', str)
DiscrepancyId = NewType('DiscrepancyId', str)


class Discrepancy(BaseModelWithObjectId):
    discrepancy_id: DiscrepancyId
    document_id: str
    discrepancy_type: DiscrepancyTypeDescription
    location: DiscrepancyLocation
    details: dict
