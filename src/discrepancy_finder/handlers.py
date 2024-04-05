from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import Any, Iterable

from loguru import logger
from pymongo.errors import BulkWriteError

from .models.base import BaseModelWithObjectId
from .models.document import DocumentId
from .models.repositories import AbstractRepositoryWithInsertMany, DocumentRepository
from .parser import Parser
from .validator import DiscrepancyFinder


class AbstractHandler(metaclass=ABCMeta):
    # https://refactoring.guru/design-patterns/chain-of-responsibility
    def __init__(self):
        self._next_handler = None

    def chain(self, handler):
        self._next_handler = handler
        return self

    @abstractmethod
    def handle(self, request: Any):
        if self._next_handler is not None:
            return self._next_handler.handle(request)
        return None


class DirectoryParsingHandler(AbstractHandler):
    def handle(self, directory: Path):
        logger.info(f"processing documents from {directory}")
        return super().handle(Parser.parse(directory))


class DatabaseHandler(AbstractHandler, metaclass=ABCMeta):
    def __init__(self, repository: AbstractRepositoryWithInsertMany):
        super().__init__()
        self.repository = repository


class DatabaseInsertHandler(DatabaseHandler):
    def handle(self, data: Iterable[BaseModelWithObjectId]):
        try:
            data = list(data)
            logger.debug(f"saving {len(data)} items to the database")
            result = self.repository.insert_many(data)
        except BulkWriteError as bwe:
            logger.error(f"an error occurred while saving data: {bwe.details}")
            result = None
            data = []

        if result is None or not result.inserted_ids:
            logger.warning("no data was inserted")
        else:
            logger.info(f"saved {len(result.inserted_ids)} items")

        return super().handle((data_item.id for data_item in data))


class DiscrepancyFinderHandler(DatabaseHandler):
    def __init__(self, repository: DocumentRepository, discrepancy_finder: DiscrepancyFinder):
        super().__init__(repository)
        self.discrepancy_finder = discrepancy_finder

    def handle(self, document_ids: Iterable[DocumentId]):
        logger.info("validating documents in the database")
        return super().handle(
            self.discrepancy_finder.find_discrepancies(
                self.repository.find_by({"id": {"$in": list(document_ids)}})
            )
        )
