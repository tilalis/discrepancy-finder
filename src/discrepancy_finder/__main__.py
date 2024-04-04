from abc import ABC
from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from loguru import logger
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

from .models.discrepancy import (
    DateIsTooFarInTheFutureOrMissing,
    Discrepancy,
    FirstRowSumIsHigherThanPermitted,
    TitleIsShorterThanPermittedOrMissing,
)
from .models.document import Document, DocumentId
from .models.repositories import (
    DiscrepancyRepository,
    DocumentRepository,
    RepositoryFactory,
)
from .parser import Parser
from .settings import Settings
from .validator import DiscrepancyFinder

logger = logger.patch(lambda record: record.update(name='discrepancy_finder'))
settings = Settings()


class AbstractHandler(ABC):
    # https://refactoring.guru/design-patterns/chain-of-responsibility
    def __init__(self):
        self._next_handler = None

    def chain(self, handler):
        self._next_handler = handler
        return handler

    def handle(self, request: Any):
        if self._next_handler is not None:
            return self._next_handler.handle(request)
        return None


class DirectoryParsingHandler(AbstractHandler):
    def handle(self, directory: Path):
        logger.info(f"processing documents from {directory}")
        return super().handle(Parser.parse(directory))


class DocumentDatabaseHandler(AbstractHandler):
    def __init__(self, repository: DocumentRepository):
        super().__init__()
        self.repository = repository


class DocumentsDatabaseInsertHandler(DocumentDatabaseHandler):
    def handle(self, documents: Iterable[Document]):
        try:
            documents = list(documents)
            logger.info(f"saving {len(documents)} documents to the database")
            result = self.repository.insert_many(documents)
        except BulkWriteError as bwe:
            logger.error(f"an error occurred while saving documents: {bwe.details}")
            result = None
            documents = []

        if result is None or not result.inserted_ids:
            logger.warning("no documents were inserted")

        return super().handle((
            document.document_id
            for document in documents
        ))


class DiscrepancyFinderHandler(DocumentDatabaseHandler):
    def __init__(self, repository: DocumentRepository, discrepancy_finder: DiscrepancyFinder):
        super().__init__(repository)
        self.discrepancy_finder = discrepancy_finder

    def handle(self, document_ids: Iterable[DocumentId]):
        logger.info("validating documents in the database")
        return super().handle(
            self.discrepancy_finder.find_discrepancies(
                self.repository.find_by({"document_id": {"$in": list(document_ids)}})
            )
        )


class DiscrepancyInsertDatabaseHandler(AbstractHandler):
    def __init__(self, repository: DiscrepancyRepository):
        super().__init__()
        self.repository = repository

    def handle(self, discrepancies: Iterable[Discrepancy]):
        try:
            discrepancies = list(discrepancies)
            logger.debug(f"saving {len(discrepancies)} discrepancies to the database")
            result = self.repository.insert_many(discrepancies)
        except BulkWriteError as bwe:
            logger.error(f"an error occurred while saving discrepancies: {bwe.details}")
            result = None

        if result is None or not result.inserted_ids:
            logger.warning("no discrepancies were inserted")
        else:
            logger.info(f"saved {len(result.inserted_ids)} discrepancies")

        return super().handle(result)


def main():
    parser = ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    logger.info(f"connecting to the database at {settings.database.url}")

    repository_factory = RepositoryFactory(MongoClient(settings.mongo_url), settings.database.name)
    document_repository, discrepancy_repository = (
        repository_factory.create_document_repository(), repository_factory.create_discrepancy_repository()
    )

    handler = DirectoryParsingHandler()

    handler.chain(
        DocumentsDatabaseInsertHandler(repository=document_repository)
    ).chain(
        DiscrepancyFinderHandler(
            repository=document_repository,
            discrepancy_finder=DiscrepancyFinder(
                TitleIsShorterThanPermittedOrMissing(min_length=2),
                DateIsTooFarInTheFutureOrMissing(max_date=datetime(2023, 1, 1)),
                FirstRowSumIsHigherThanPermitted(max_sum=5220),
            )
        )
    ).chain(
        DiscrepancyInsertDatabaseHandler(repository=discrepancy_repository)
    )

    try:
        handler.handle(args.directory)
    except Exception as e:
        logger.exception(f"an error occurred: {e}")

    logger.info("done")


if __name__ == '__main__':
    main()
