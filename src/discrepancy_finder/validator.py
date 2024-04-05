import functools
import time
from enum import Enum
from typing import Iterable, NamedTuple, Optional

from loguru import logger
from typing_extensions import NotRequired, TypedDict

from .models.discrepancy import (
    Discrepancy,
    DiscrepancyLocation,
    DiscrepancyType,
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
                yield from func(*args, **kwargs)
            except exception_types as e:
                yield return_value if not callable(return_value) else return_value(e, *args, **kwargs)

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
    rule_name: NotRequired[str]
    rule_parameters: NotRequired[dict]
    rule_description: NotRequired[str]
    location: NotRequired[DiscrepancyLocation]
    error: NotRequired[str]


class ValidationResult(NamedTuple):
    status: ValidationStatus
    info: ValidationResultInfo


class DocumentValidator:
    # https://refactoring.guru/design-patterns/strategy, as a Strategy context
    def __init__(
            self,
            *rules: DiscrepancyType,
    ):
        self.rules = rules

    @on_exception(lambda exception, _, document: ValidationResult(
        status=ValidationStatus.ERROR, info={'document_id': document.document_id, 'error': str(exception)}
    ))
    def validate(self, document: Optional[Document]) -> ValidationResult:
        if document is None:
            yield ValidationResult(
                status=ValidationStatus.NOT_FOUND,
                info={}
            )
            return

        valid_rules = 0
        for rule in self.rules:
            is_valid, location = rule.check(document)

            if is_valid:
                valid_rules += 1
                continue

            yield ValidationResult(
                status=ValidationStatus.INVALID,
                info={
                    'rule_name': str(rule),
                    'rule_description': rule.description,
                    'rule_parameters': rule.parameters,
                    'document_id': document.document_id,
                    'location': location
                }
            )

        if len(self.rules) == valid_rules:
            yield ValidationResult(
                status=ValidationStatus.VALID,
                info={'document_id': document.document_id}
            )


class DiscrepancyFinder:
    # https://refactoring.guru/design-patterns/facade
    def __init__(
            self,
            *rules: DiscrepancyType,
    ):
        self.rules = rules

    def create_validator(self):
        return DocumentValidator(
            *self.rules,
        )

    def find_discrepancies(self, documents: Iterable[Document]) -> Iterable[Discrepancy]:
        validator = self.create_validator()

        for document in documents:
            logger.info(f'validating document {document.document_id}')

            for result in validator.validate(document):
                if result.status == ValidationStatus.VALID:
                    logger.debug(f'document {document.document_id} is valid')
                    continue

                if result.status == ValidationStatus.ERROR:
                    logger.error(f'error validating document {document.document_id}: {result.info["error"]}')
                    yield Discrepancy(
                        document_id=document.document_id,
                        discrepancy_id=f'{document.document_id}error',
                        discrepancy_type=DiscrepancyTypeDescription('Error'),
                        details=result.info
                    )
                    continue

                discrepancy_description, rule_name = result.info['rule_description'], result.info['rule_name']
                logger.debug(f'found discrepancy for document {document.document_id}: {discrepancy_description}')

                yield Discrepancy(
                    document_id=document.document_id,
                    discrepancy_id=f'{document.document_id}{rule_name}',
                    discrepancy_type=DiscrepancyTypeDescription(result.info['rule_name']),
                    location=result.info.get('location'),
                    details=result.info
                )
