import uuid

from pydantic import BaseModel


class RebuildEmbeddingsResponse(BaseModel):
    object_type: str
    collection_name: str
    model_version_id: uuid.UUID
    total: int
    embedded: int
    skipped: int
