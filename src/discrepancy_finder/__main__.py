from pathlib import Path
from argparse import ArgumentParser

from loguru import logger
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

from discrepancy_finder.settings import Settings
from discrepancy_finder.models.repositories import DocumentRepository
from discrepancy_finder.parser import Parser

logger = logger.patch(lambda record: record.update(name='discrepancy_finder'))
settings = Settings()

logger.info(f"connecting to the database at {settings.database.url}")
client = MongoClient(settings.mongo_url)
database = client[settings.database.name]
document_repository = DocumentRepository(database)


def main():
    parser = ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    logger.info(f"processing documents from {args.directory}")
    documents = list(Parser.parse(args.directory))
    logger.info(f"saving {len(documents)} documents to the database")

    try:
        result = document_repository.insert_many(documents)
    except BulkWriteError as bwe:
        logger.error(f"an error occurred while saving documents: {bwe.details}")
        return

    if not result.inserted_ids:
        logger.warning("no documents were inserted")

    logger.debug(f"inserted {len(result.inserted_ids)} out of {len(documents)} documents")
    logger.info("done")


if __name__ == '__main__':
    main()
