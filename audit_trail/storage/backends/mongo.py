"""MongoDB storage backend for audit trail events."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pymongo import MongoClient
from bson import ObjectId

from .base import BaseStorageBackend


class MongoStorageBackend(BaseStorageBackend):
    """Persist audit events into a MongoDB collection."""

    def __init__(self, *, config: Dict[str, Any]):
        """Configure the MongoDB client and ensure indexes exist."""

        super().__init__(config=config)
        uri = config.get("uri", "mongodb://localhost:27017")
        database = config.get("database", "audit_trail")
        collection = config.get("collection", "events")
        self.client = MongoClient(uri, tls=config.get("tls", True))
        self.collection = self.client[database][collection]
        self.collection.create_index([("object_id", 1), ("timestamp", -1)])
        self.collection.create_index([("actor.id", 1), ("timestamp", -1)])

    def store_event(self, payload: Dict[str, Any]) -> None:
        """Insert the audit payload as a MongoDB document."""

        self.collection.insert_one(payload)

    def fetch_object_events(
        self,
        *,
        model: str | None,
        object_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        query: Dict[str, Any] = {"object_id": object_id}
        if cursor:
            query["_id"] = {"$lt": ObjectId(cursor)}
        docs = list(self.collection.find(query).sort("_id", -1).limit(limit))
        next_cursor = str(docs[-1]["_id"]) if len(docs) == limit else None
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs, next_cursor

    def fetch_user_events(
        self,
        *,
        user_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        query: Dict[str, Any] = {"actor.id": user_id}
        if cursor:
            query["_id"] = {"$lt": ObjectId(cursor)}
        docs = list(self.collection.find(query).sort("_id", -1).limit(limit))
        next_cursor = str(docs[-1]["_id"]) if len(docs) == limit else None
        for doc in docs:
            doc["_id"] = str(doc["_id"])
        return docs, next_cursor
