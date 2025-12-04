from __future__ import annotations

from django.core.management.base import BaseCommand

from audit_trail.tasks import dispatch_outbox, _run_dispatch
from django.conf import settings


class Command(BaseCommand):
    help = "Backfill audit events by draining the outbox synchronously"

    def add_arguments(self, parser):  # noqa: ANN001
        parser.add_argument("--batch", type=int, default=100)

    def handle(self, *args, **options):  # noqa: ANN001
        batch = options["batch"]
        processed = 0
        if getattr(settings, "AUDITTRAIL_USE_CELERY", False):
            self.stdout.write(
                self.style.WARNING(
                    "AUDITTRAIL_USE_CELERY is enabled; "
                    "this command will run the dispatcher synchronously regardless."
                )
            )
            processed = dispatch_outbox.apply_async(args=(batch,)).get()
        else:
            try:
                eager_result = dispatch_outbox.apply(args=(batch,))
                return int(eager_result.get())
            except Exception as exc:  # pragma: no cover - fallback path
                self.stdout.write(
                    self.style.WARNING(
                        "dispatch_outbox.apply failed (%s); falling back to direct call",
                        exc,
                    )
                )
                processed = _run_dispatch(batch)
        self.stdout.write(self.style.SUCCESS(f"Processed {processed} events"))
