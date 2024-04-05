from pydantic import BaseModel
from pydantic_mongo import ObjectIdField


class BaseModelWithObjectId(BaseModel):
    id: ObjectIdField = None
