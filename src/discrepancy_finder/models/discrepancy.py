from abc import ABC, abstractmethod
from datetime import datetime
from typing import NewType, Optional

from .base import BaseModelWithObjectId
from .document import Document

DiscrepancyLocation = NewType('DiscrepancyLocation', str)
DiscrepancyTypeDescription = NewType('DiscrepancyTypeDescription', str)
DiscrepancyId = NewType('DiscrepancyId', str)


class Discrepancy(BaseModelWithObjectId):
    discrepancy_id: DiscrepancyId
    document_id: str
    discrepancy_type: DiscrepancyTypeDescription
    location: DiscrepancyLocation
    details: dict


class DiscrepancyType(ABC):
    # https://refactoring.guru/design-patterns/template-method
    # also https://refactoring.guru/design-patterns/strategy, as a Strategy interface
    """
    This class implements __str__ so that it would be easily converted to a string stored in the database.
    The string representation of this class is the name of the class.
    """

    def __init__(self, description: str, **parameters):
        self.description = description
        self.parameters = parameters

    def __str__(self):
        return self.__class__.__name__

    @abstractmethod
    def check(self, document: Document) -> (bool, DiscrepancyLocation):
        pass


class TitleIsShorterThanPermittedOrMissing(DiscrepancyType):
    def __init__(self, min_length: int):
        super().__init__(f'Title length should be at least {min_length} characters', min_length=min_length)
        self.min_length = min_length

    def check(self, document: Document) -> (bool, Optional[DiscrepancyLocation]):
        return (
            (document.title is not None and len(document.title) >= self.min_length),
            DiscrepancyLocation("$.title")
        )


class DateIsTooFarInTheFutureOrMissing(DiscrepancyType):
    def __init__(self, max_date: datetime):
        super().__init__(f'Date should be present and be before {max_date}', max_date=max_date)
        self.max_date = max_date

    def check(self, document: Document) -> (bool, Optional[DiscrepancyLocation]):
        return (
            (document.date_of_creation is not None and document.date_of_creation <= self.max_date),
            DiscrepancyLocation("$.date_of_creation")
        )


class FirstRowSumIsHigherThanPermitted(DiscrepancyType):
    def __init__(self, max_sum: float):
        super().__init__(f'The sum of the first row should not exceed {max_sum}', max_sum=max_sum)
        self.max_sum = max_sum

    def check(self, document: Document) -> (bool, Optional[DiscrepancyLocation]):
        if not document.body or not document.body[0].body:
            return True, None

        first_row, first_row_sum = document.body[0].body, 0
        for index, number in enumerate(first_row):
            first_row_sum += number
            if first_row_sum > self.max_sum:
                return False, DiscrepancyLocation(f"$.body[0].body[{index}]")

        return True, None
