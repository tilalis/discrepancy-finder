from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

from loguru import logger
from pymongo import MongoClient

from .handlers import (
    DatabaseInsertHandler,
    DirectoryParsingHandler,
    DiscrepancyFinderHandler,
)
from .models.discrepancy import (
    DateIsTooFarInTheFutureOrMissing,
    FirstRowSumIsHigherThanPermitted,
    TitleIsShorterThanPermittedOrMissing,
)
from .models.repositories import RepositoryFactory
from .settings import Settings
from .validator import DiscrepancyFinder

logger = logger.patch(lambda record: record.update(name='discrepancy_finder'))
settings = Settings()
repository_factory = RepositoryFactory(MongoClient(settings.mongo_url), settings.database.name)


def main():
    parser = ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()

    logger.info(f"connecting to the database at {settings.database.url}")
    document_repository, discrepancy_repository = (
        repository_factory.create_document_repository(), repository_factory.create_discrepancy_repository()
    )

    discrepancy_finder = DiscrepancyFinder(
        TitleIsShorterThanPermittedOrMissing(min_length=2),
        DateIsTooFarInTheFutureOrMissing(max_date=datetime(2023, 1, 1)),
        FirstRowSumIsHigherThanPermitted(max_sum=5220),
    )

    try:
        DirectoryParsingHandler().chain(
            DatabaseInsertHandler(repository=document_repository).chain(
                DiscrepancyFinderHandler(
                    repository=document_repository,
                    discrepancy_finder=discrepancy_finder
                ).chain(
                    DatabaseInsertHandler(repository=discrepancy_repository)
                )
            )
        ).handle(args.directory)
    except Exception as e:
        logger.exception(f"an error occurred: {e}")

    logger.info("done")


if __name__ == '__main__':
    main()
