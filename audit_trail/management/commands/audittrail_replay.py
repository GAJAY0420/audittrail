from __future__ import annotations

from django.core.management.base import BaseCommand

from audit_trail.storage.outbox.models import AuditEventOutbox


class Command(BaseCommand):
    help = "Replay dead-lettered audit events"

    def handle(self, *args, **options):  # noqa: ANN001
        updated = AuditEventOutbox.objects.filter(status="dlq").update(
            status="pending", attempts=0
        )
        self.stdout.write(self.style.SUCCESS(f"Re-queued {updated} events"))
