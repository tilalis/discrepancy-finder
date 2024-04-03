from typing import Iterable, Generic

from pydantic_mongo import AbstractRepository
from pydantic_mongo.abstract_repository import T
from pymongo.results import InsertManyResult

from .discrepancy import Discrepancy
from .document import Document


class AbstractRepositoryWithInsertMany(AbstractRepository, Generic[T]):
    def insert_many(self, models: Iterable[T]) -> InsertManyResult:
        """
        This method, unlike the original save_many, returns the result of the insert_many operation.
        :param models:
        :return:
        """
        models_to_insert = [
            model for model in models if model.id is None
        ]

        if not models_to_insert:
            return InsertManyResult([], False)

        result = self.get_collection().insert_many((self.to_document(model) for model in models_to_insert))

        for idx, inserted_id in enumerate(result.inserted_ids):
            models_to_insert[idx].document_id = inserted_id

        return result


class DocumentRepository(AbstractRepositoryWithInsertMany[Document]):
    class Meta:
        collection_name = 'documents'


class DiscrepancyRepository(AbstractRepositoryWithInsertMany[Discrepancy]):
    class Meta:
        collection_name = 'discrepancies'
