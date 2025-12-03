"""Kafka streaming publisher implementation."""

from __future__ import annotations

import json
from typing import Any, Dict

from confluent_kafka import Producer

from .base import BaseStreamPublisher


class KafkaPublisher(BaseStreamPublisher):
    """Publish audit events to a Kafka topic."""

    def __init__(self, config: Dict[str, Any]):
        """Configure the Kafka producer instance.

        Args:
            config: Mapping of Kafka producer options, including `topic` and
                `bootstrap_servers`.
        """
        super().__init__(config)
        self.topic = config.get("topic", "audit-events")
        self.producer = Producer(
            {"bootstrap.servers": config.get("bootstrap_servers", "localhost:9092")}
        )

    def publish(self, event: Dict[str, Any]) -> None:
        """Serialize the audit event and enqueue it to Kafka.

        Args:
            event: The audit event payload to publish.
        """
        self.producer.produce(self.topic, value=json.dumps(event))
        self.producer.poll(0)
