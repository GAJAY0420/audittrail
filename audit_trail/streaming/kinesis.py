"""Kinesis streaming publisher implementation."""

from __future__ import annotations

import json
from typing import Any, Dict

import boto3
from botocore.config import Config

from .base import BaseStreamPublisher


class KinesisPublisher(BaseStreamPublisher):
    """Publish audit events to AWS Kinesis."""

    def __init__(self, config: Dict[str, Any]):
        """Configure the Kinesis client used for publishing.

        Args:
            config: Mapping of Kinesis options such as `stream` and `region`.
        """
        super().__init__(config)
        self.stream_name = config.get("stream", "audit-stream")
        region = config.get("region", "us-east-1")
        self.client = boto3.client(
            "kinesis",
            region_name=region,
            config=Config(read_timeout=5, retries={"max_attempts": 3}),
        )

    def publish(self, event: Dict[str, Any]) -> None:
        """Send the serialized audit event to the configured Kinesis stream.

        Args:
            event: The audit event payload to publish.
        """
        partition_key = event.get("object_id", "unknown")
        self.client.put_record(
            StreamName=self.stream_name,
            Data=json.dumps(event),
            PartitionKey=partition_key,
        )
