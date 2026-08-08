from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, File, Form, UploadFile

from app.knowledge_contracts import (
    KnowledgeCollection,
    KnowledgeCollectionCreate,
    KnowledgeCollectionList,
    KnowledgeDeleteResult,
    KnowledgeDocument,
    KnowledgeDocumentMutation,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    RightsBasis,
)
from app.services.knowledge import KnowledgeService


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@lru_cache(maxsize=1)
def get_knowledge_service() -> KnowledgeService:
    return KnowledgeService.from_environment()


@router.post("/collections", response_model=KnowledgeCollection)
def create_collection(request: KnowledgeCollectionCreate) -> dict:
    return get_knowledge_service().create_collection(request.name)


@router.get("/collections", response_model=KnowledgeCollectionList)
def list_collections() -> dict:
    return {"collections": get_knowledge_service().list_collections()}


@router.get("/collections/{collection_id}", response_model=KnowledgeCollection)
def get_collection(collection_id: str) -> dict:
    return get_knowledge_service().get_collection(collection_id)


@router.delete("/collections/{collection_id}", response_model=KnowledgeDeleteResult)
def delete_collection(collection_id: str) -> dict:
    return get_knowledge_service().delete_collection(collection_id)


@router.post(
    "/collections/{collection_id}/documents",
    response_model=KnowledgeDocumentMutation,
)
async def add_document(
    collection_id: str,
    file: UploadFile = File(...),
    rights_basis: RightsBasis = Form(...),
    source_url: str | None = Form(None),
) -> dict:
    return get_knowledge_service().add_document(
        collection_id,
        file.filename or "upload",
        await file.read(),
        rights_basis=rights_basis,
        source_url=source_url,
    )


@router.get(
    "/collections/{collection_id}/documents/{document_id}",
    response_model=KnowledgeDocument,
)
def get_document(collection_id: str, document_id: str) -> dict:
    return get_knowledge_service().get_document(collection_id, document_id)


@router.post(
    "/collections/{collection_id}/documents/{document_id}/replace",
    response_model=KnowledgeDocumentMutation,
)
async def replace_document(
    collection_id: str,
    document_id: str,
    file: UploadFile = File(...),
    rights_basis: RightsBasis = Form(...),
    source_url: str | None = Form(None),
) -> dict:
    return get_knowledge_service().replace_document(
        collection_id,
        document_id,
        file.filename or "upload",
        await file.read(),
        rights_basis=rights_basis,
        source_url=source_url,
    )


@router.delete(
    "/collections/{collection_id}/documents/{document_id}",
    response_model=KnowledgeDeleteResult,
)
def delete_document(collection_id: str, document_id: str) -> dict:
    return get_knowledge_service().delete_document(collection_id, document_id)


@router.post("/collections/{collection_id}/reindex", response_model=KnowledgeCollection)
def reindex_collection(collection_id: str) -> dict:
    return get_knowledge_service().reindex(collection_id)


@router.post(
    "/collections/{collection_id}/search",
    response_model=KnowledgeSearchResponse,
)
def search_collection(collection_id: str, request: KnowledgeSearchRequest) -> dict:
    return get_knowledge_service().search(collection_id, request.query, request.top_k)

