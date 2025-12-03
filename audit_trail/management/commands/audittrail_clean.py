from __future__ import annotations

from django.core.management.base import BaseCommand

from audit_trail.storage.outbox.cleanup_tasks import (
    purge_sent_entries,
    release_stuck_entries,
)


class Command(BaseCommand):
    help = "Clean audit outbox entries"

    def handle(self, *args, **options):  # noqa: ANN001
        released = release_stuck_entries()
        purged = purge_sent_entries()
        self.stdout.write(
            self.style.SUCCESS(f"Released {released} locks, purged {purged} entries")
        )
