"""Amazon S3 storage backend for audit events."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Tuple

import boto3
from botocore.config import Config

from .base import BaseStorageBackend


class S3StorageBackend(BaseStorageBackend):
    """Persist audit events as JSON objects within an S3 bucket."""

    def __init__(self, *, config: Dict[str, Any]):
        """Configure the S3 client and storage prefix."""

        super().__init__(config=config)
        self.bucket = config.get("bucket", "audit-trail-events")
        self.object_prefix = config.get("prefix", "events/")
        self.user_prefix = config.get("user_prefix", "users/")
        region = config.get("region", "us-east-1")
        self.client = boto3.client(
            "s3", region_name=region, config=Config(signature_version="s3v4")
        )

    def store_event(self, payload: Dict[str, Any]) -> None:
        """Upload the payload JSON to S3 with server-side encryption."""

        key = f"{self.object_prefix}{payload['object_id']}/{payload['timestamp']}--{payload['event_id']}.json"
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ServerSideEncryption="AES256",
        )
        actor = payload.get("actor") or {}
        user_id = actor.get("id")
        if user_id:
            user_key = f"{self.user_prefix}{user_id}/{payload['timestamp']}--{payload['event_id']}.json"
            self.client.put_object(
                Bucket=self.bucket,
                Key=user_key,
                Body=json.dumps(payload).encode("utf-8"),
                ServerSideEncryption="AES256",
            )

    def fetch_object_events(
        self,
        *,
        model: str | None,
        object_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        prefix = f"{self.object_prefix}{object_id}/"
        return self._fetch_events(prefix=prefix, limit=limit, cursor=cursor)

    def fetch_user_events(
        self,
        *,
        user_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        prefix = f"{self.user_prefix}{user_id}/"
        return self._fetch_events(prefix=prefix, limit=limit, cursor=cursor)

    def _fetch_events(
        self, *, prefix: str, limit: int, cursor: str | None
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        keys = self._list_keys(prefix)
        if not keys:
            return [], None
        start_index = 0
        decoded_cursor = self._decode_cursor(cursor)
        if decoded_cursor:
            try:
                start_index = keys.index(decoded_cursor) + 1
            except ValueError:
                start_index = 0
        slice_keys = keys[start_index : start_index + limit]
        if not slice_keys:
            return [], None
        events: List[Dict[str, Any]] = []
        for key in slice_keys:
            obj = self.client.get_object(Bucket=self.bucket, Key=key)
            body = obj["Body"].read()
            events.append(json.loads(body))
        next_cursor = (
            self._encode_cursor(slice_keys[-1]) if len(slice_keys) == limit else None
        )
        return events, next_cursor

    def _list_keys(self, prefix: str) -> List[str]:
        paginator = self.client.get_paginator("list_objects_v2")
        keys: List[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for content in page.get("Contents", []):
                keys.append(content["Key"])
        keys.sort(reverse=True)
        return keys

    @staticmethod
    def _encode_cursor(key: str | None) -> str | None:
        if not key:
            return None
        return base64.b64encode(key.encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str | None) -> str | None:
        if not cursor:
            return None
        try:
            return base64.b64decode(cursor.encode()).decode()
        except ValueError:
            return None
