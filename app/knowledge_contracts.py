from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


RightsBasis = Literal[
    "created_by_user",
    "permission_or_license",
    "public_domain",
    "other_authorized_research_use",
]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class KnowledgeCollectionCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)


class KnowledgeDocument(StrictModel):
    document_id: str
    collection_id: str
    display_name: str
    media_type: Literal["text/plain", "text/markdown"]
    size_bytes: int = Field(ge=1)
    normalized_bytes: int = Field(ge=1)
    sha256: str
    revision: int = Field(ge=1)
    state: Literal["ready"]
    rights_basis: RightsBasis
    source_url: str | None = None
    created_at: datetime
    updated_at: datetime


class KnowledgeCollection(StrictModel):
    collection_id: str
    display_name: str
    state: Literal["ready"]
    provider_access_mode: Literal["local_only"]
    active_index_version: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime
    document_count: int = Field(ge=0)
    normalized_bytes: int = Field(ge=0)
    documents: list[KnowledgeDocument]


class KnowledgeCollectionList(StrictModel):
    collections: list[KnowledgeCollection]


class KnowledgeDocumentMutation(StrictModel):
    duplicate: bool
    document: KnowledgeDocument


class KnowledgeSearchRequest(StrictModel):
    query: str = Field(min_length=1, max_length=2_000)
    top_k: int = Field(default=3, ge=1, le=5)


class KnowledgeSearchMatch(StrictModel):
    chunk_id: str
    document_id: str
    document_revision: int = Field(ge=1)
    display_name: str
    source_url: str | None = None
    rights_basis: RightsBasis
    position: int = Field(ge=0)
    excerpt: str
    score: float = Field(gt=0)


class KnowledgeSearchResponse(StrictModel):
    query: str
    collection_id: str
    index_version: int = Field(ge=0)
    evidence_label: Literal["user_provided"]
    matches: list[KnowledgeSearchMatch]


class KnowledgeDeleteResult(StrictModel):
    deleted: Literal[True]
    collection_id: str
    document_id: str | None = None
    document_count: int | None = None

