"""Management command that seeds demo data to trigger audit events."""

from __future__ import annotations

import json
from typing import Any, Dict

from django.core.management.base import BaseCommand, CommandError

from audit_trail.models import AuditDemoRecord


class Command(BaseCommand):
    """Create demo records with numeric, text, and JSON content."""

    help = "Create demo audit records so developers can verify end-to-end capture"

    def add_arguments(self, parser) -> None:  # type: ignore[override]
        """Define CLI arguments for the command."""

        parser.add_argument(
            "--count",
            type=int,
            default=5,
            help="Number of demo records to insert.",
        )
        parser.add_argument(
            "--prefix",
            type=str,
            default="Sample audit event",
            help="Prefix for the generated message text.",
        )
        parser.add_argument(
            "--payload",
            type=str,
            default="{}",
            help="JSON object merged into every structured payload.",
        )
        parser.add_argument(
            "--start",
            type=int,
            default=1,
            help="Starting integer to use for the numeric field.",
        )

    def handle(self, *args, **options) -> None:  # noqa: ANN001
        """Execute the command and generate the requested demo records."""

        count: int = max(0, options.get("count", 0))
        prefix: str = options.get("prefix", "Sample audit event")
        payload_raw: str = options.get("payload", "{}")
        starting_number: int = options.get("start", 1)
        try:
            parsed_payload: Any = json.loads(payload_raw)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive guard
            raise CommandError("--payload must be valid JSON") from exc
        if parsed_payload and not isinstance(parsed_payload, dict):
            raise CommandError("--payload must decode to a JSON object")

        payload_dict: Dict[str, Any] | None = (
            dict(parsed_payload) if isinstance(parsed_payload, dict) else None
        )

        created = AuditDemoRecord.objects.seed_records(
            count=count,
            prefix=prefix,
            base_payload=payload_dict,
            starting_number=starting_number,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(created)} demo record(s); audit events enqueued via the outbox."
            )
        )
