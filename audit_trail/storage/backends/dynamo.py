"""DynamoDB storage backend for persisting audit events."""

from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Tuple

import boto3
from botocore.config import Config
from django.conf import settings

from .base import BaseStorageBackend


def _encode_cursor(last_evaluated_key):
    if not last_evaluated_key:
        return None
    return base64.b64encode(json.dumps(last_evaluated_key).encode()).decode()


def _decode_cursor(cursor):
    if not cursor:
        return None
    return json.loads(base64.b64decode(cursor).decode())


class DynamoStorageBackend(BaseStorageBackend):
    """Write audit events into an AWS DynamoDB table."""

    def __init__(self, *, config: Dict[str, Any]):
        """Configure the DynamoDB resource and target table."""

        super().__init__(config=config)
        table_name = config.get("table", "audit_events")
        region = config.get("region", "us-east-1")
        self.client = boto3.resource(
            "dynamodb", region_name=region, config=Config(retries={"max_attempts": 5})
        )
        self.table = self.client.Table(table_name)

    def _pk(self, tenant_id: str, model: str) -> str:
        return f"TENANT#{tenant_id}#MODEL#{model}"

    def _sk(self, ts_iso: str, object_id: str, event_id: str) -> str:
        return f"TS#{ts_iso}#OBJ#{object_id}#EVT#{event_id}"

    def store_event(self, event: Dict[str, Any]) -> None:
        """Persist the payload as an item in DynamoDB."""

        tenant_id = settings.TENANT_ID if hasattr(settings, "TENANT_ID") else "default"
        model = event["model"]
        object_id = event["object_id"]
        timestamp = event["timestamp"]
        event_id = event["event_id"]

        item: dict[str, Any] = {
            "pk": self._pk(tenant_id, model),
            "sk": self._sk(timestamp, object_id, event_id),
            "tenant_id": tenant_id,
            "model": model,
            "object_id": object_id,
            "event_type": event["event_type"],
            "timestamp": timestamp,
            "actor": event.get("actor"),
            "diff": event.get("diff", {}),
            "request": event.get("context", {}).get("request", {}),
            "event_id": event_id,
            "summary": event.get("summary", ""),
            # GSIs
            "gsi1pk": f"OBJ#{object_id}",
            "gsi1sk": f"TS#{timestamp}",
            "gsi2pk": f"USER#{event.get('actor', {}).get('id', 'anonymous')}",
            "gsi2sk": f"TS#{timestamp}",
        }

        self.table.put_item(Item=item)

    def fetch_object_events(
        self,
        *,
        model: str | None,
        object_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        params: dict[str, Any] = {
            "IndexName": "gsi1",  # must exist on the table
            "KeyConditionExpression": "gsi1pk = :obj",
            "ExpressionAttributeValues": {":obj": f"OBJ#{object_id}"},
            "ScanIndexForward": False,  # newest first
            "Limit": limit,
        }
        lek = _decode_cursor(cursor)
        if lek:
            params["ExclusiveStartKey"] = lek

        resp = self.table.query(**params)
        items = resp.get("Items", [])
        next_cursor = _encode_cursor(resp.get("LastEvaluatedKey"))
        return items, next_cursor

    def fetch_user_events(
        self,
        *,
        user_id: str,
        limit: int = 50,
        cursor: str | None = None,
    ) -> Tuple[List[Dict[str, Any]], str | None]:
        params: dict[str, Any] = {
            "IndexName": "gsi2",  # must exist on the table
            "KeyConditionExpression": "gsi2pk = :u",
            "ExpressionAttributeValues": {":u": f"USER#{user_id}"},
            "ScanIndexForward": False,
            "Limit": limit,
        }
        lek = _decode_cursor(cursor)
        if lek:
            params["ExclusiveStartKey"] = lek

        resp = self.table.query(**params)
        items = resp.get("Items", [])
        next_cursor = _encode_cursor(resp.get("LastEvaluatedKey"))
        return items, next_cursor
