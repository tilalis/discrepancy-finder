import functools
import inspect
import itertools
from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Iterable, NamedTuple, Optional, cast

from loguru import logger
from typing_extensions import NotRequired, TypedDict

from .models.discrepancy import (
    Discrepancy,
    DiscrepancyLocation,
    DiscrepancyTypeDescription,
)
from .models.document import Document


def on_exception(return_value, exception_types=(Exception,)):
    # https://refactoring.guru/design-patterns/decorator
    """
    Decorator that catches exceptions and returns a default value or the result of a function.
    :param return_value:
        value to return if an exception is caught, can be callable,
        if it is callable, it will be called with the exception as its first argument,
        followed by *args and **kwargs of the decorated function
    :param exception_types: types of exceptions to catch
    :return: a wrapper function that catches exceptions in decorated function
    """

    def on_exception_decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                return return_value if not callable(return_value) else return_value(e, *args, **kwargs)

        return wrapper

    return on_exception_decorator


class ValidationStatus(Enum):
    VALID = 'valid'
    INVALID = 'invalid'
    ERROR = 'error'
    NOT_FOUND = 'not_found'
    NOT_PROCESSED = 'not_processed'


class ValidationResultInfo(TypedDict):
    document_id: NotRequired[str]
    rule: NotRequired[str]
    rule_parameters: NotRequired[dict]
    location: NotRequired[str]
    error: NotRequired[str]


class ValidationResult(NamedTuple):
    status: ValidationStatus
    info: ValidationResultInfo


class DocumentValidatorMeta(ABCMeta):
    def __new__(mcs, name, bases, attrs):
        cls = super().__new__(mcs, name, bases, attrs)

        if inspect.isabstract(cls):
            return cls

        if "location" not in attrs:
            raise AttributeError(f"{cls.__name__} should have `location` class-level attribute")

        return cls


class DocumentValidator(ABC, metaclass=DocumentValidatorMeta):
    location: DiscrepancyLocation
    # also https://refactoring.guru/design-patterns/strategy, as a Strategy interface
    """
    This class implements __str__ so that it can be easily converted to a string to be stored in the database.
    The string representation of this class is the name of the class.
    """

    def __str__(self):
        return self.__class__.__name__

    @property
    def name(self):
        return str(self)

    def get_info(
            self, document: Document,
            override_location: Optional[DiscrepancyLocation] = None,
            error: Optional[Exception] = None
    ) -> ValidationResultInfo:
        parameters = vars(self)

        result = {
            'document_id': document.document_id,
            'rule': str(self),
            'rule_parameters': parameters,
            'location': (
                str(self.location if override_location is None else cast(override_location, DiscrepancyLocation))
            )
        }

        if error is not None:
            result['error'] = str(error)

        return result

    def create_result(
            self,
            status: ValidationStatus,
            document: Document,
            override_location: Optional[DiscrepancyLocation] = None,
            error: Optional[Exception] = None
    ) -> ValidationResult:
        return ValidationResult(
            status=status,
            info=self.get_info(document, override_location, error)
        )

    @abstractmethod
    def validate(self, document: Document) -> ValidationResult:
        """
        This method validates the document

        It is an abstract method of DocumentValidator, it returns a result with VALID status.

        DocumentValidator subclasses are expected to call its parent `validate` method on success instead of providing
        a success result. It allows to re-use and generalize validator classes.

        :param document:
        :return: an instance of ValidationResult
        """
        return self.create_result(ValidationStatus.VALID, document=document)


# this decorator is designed to be applied
# to DocumentValidator subclasses instead of default exception handling in base class
default_on_exception = on_exception(
    lambda exception, obj, document: obj.create_result(
        ValidationStatus.ERROR,
        document,
        error=exception
    )
)


class TitleIsShorterThanPermittedOrMissing(DocumentValidator):
    location = DiscrepancyLocation("$.title"),

    def __init__(self, min_length: int):
        self.min_length = min_length

    @default_on_exception
    def validate(self, document: Document) -> ValidationResult:
        has_title = document.title is not None
        title_has_permitted_length = has_title and len(document.title) >= self.min_length

        if has_title and title_has_permitted_length:
            return self.create_result(
                ValidationStatus.VALID,
                document=document
            )

        if not has_title:
            return self.create_result(
                ValidationStatus.NOT_FOUND,
                document=document
            )

        return super().validate(document)


class DateIsTooFarInTheFutureOrMissing(DocumentValidator):
    location = DiscrepancyLocation("$.date_of_creation"),

    def __init__(self, max_date: datetime):
        self.max_date = max_date

    @default_on_exception
    def validate(self, document: Document) -> ValidationResult:
        has_date = document.date_of_creation is not None
        date_is_before_max = has_date and document.date_of_creation <= self.max_date

        if has_date and date_is_before_max:
            return self.create_result(
                ValidationStatus.VALID,
                document=document
            )

        if not has_date:
            return self.create_result(
                ValidationStatus.NOT_FOUND,
                document=document
            )

        return super().validate(document)


class FirstRowSumIsGreaterThanPermitted(DocumentValidator):
    location = DiscrepancyLocation(f"$.body[0]")

    def __init__(self, max_sum: float):
        self.max_sum = max_sum

    @default_on_exception
    def validate(self, document: Document) -> ValidationResult:
        has_body = bool(document.body) and bool(document.body[0].body)

        if not has_body:
            return self.create_result(
                ValidationStatus.NOT_FOUND,
                document
            )

        first_row, first_row_sum = document.body[0].body, 0
        for index, number in enumerate(first_row):
            first_row_sum += number
            if first_row_sum > self.max_sum:
                return self.create_result(
                    ValidationStatus.INVALID,
                    document,
                    override_location=DiscrepancyLocation(f"$.body[0].body[{index}]")
                )

        return super().validate(document)


class DiscrepancyFinder:
    # https://refactoring.guru/design-patterns/strategy, as Strategy context
    def __init__(
            self,
            *validators: DocumentValidator,
    ):
        self.validators = validators

    def find_discrepancies(self, documents: Iterable[Document]) -> Iterable[Discrepancy]:
        for document, validator in itertools.product(documents, self.validators):
            logger.info(f'{validator}: validating document {document.document_id}')

            result = validator.validate(document)

            if result.status == ValidationStatus.VALID:
                logger.debug(f'{validator}: document {document.document_id} is valid')
                continue

            if result.status == ValidationStatus.ERROR:
                logger.error(
                    f'{validator}: error validating document {document.document_id}, {result.info["error"]}')
                error = result.info['error']
                yield Discrepancy(
                    document_id=document.document_id,
                    discrepancy_id=f'{document.document_id}error{error}',
                    discrepancy_type=DiscrepancyTypeDescription('Error'),
                    location=result.info['location'],
                    details=result.info
                )
                continue

            rule_name = result.info['rule']
            logger.debug(f'{validator}: found discrepancy for document {document.document_id}')

            yield Discrepancy(
                document_id=document.document_id,
                discrepancy_id=f'{document.document_id}{rule_name}',
                discrepancy_type=DiscrepancyTypeDescription(rule_name),
                location=result.info.get('location'),
                details=result.info
            )
