from __future__ import annotations

from collections import Counter

from django.core.management.base import BaseCommand

from audit_trail.storage.outbox.models import AuditEventOutbox


class Command(BaseCommand):
    help = "Show audit outbox statistics"

    def handle(self, *args, **options):  # noqa: ANN001
        counter = Counter(AuditEventOutbox.objects.values_list("status", flat=True))
        for status, count in counter.items():
            self.stdout.write(f"{status}: {count}")
