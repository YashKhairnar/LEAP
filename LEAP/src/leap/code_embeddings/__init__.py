"""Frozen code-embedding component."""

from .encoder import CodeEncoder
from .store import EmbeddingLookup, code_sha256, generate_embedding_store, load_embedding_store

__all__ = [
    "CodeEncoder",
    "EmbeddingLookup",
    "code_sha256",
    "generate_embedding_store",
    "load_embedding_store",
]
