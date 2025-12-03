# Local Testing Guide for Audit Trail

This guide provides step-by-step instructions for testing the `tiger_audit_trail` application locally.

## Prerequisites

- Python 3.13+
- Django 5.2+
- Redis (for Celery)
- PostgreSQL (optional, can use SQLite for basic testing, but Postgres recommended for JSONField/Outbox)

## 1. Setup Local Environment

1.  **Install Dependencies**:
    ```bash
    pip install -e .[dev]
    ```

2.  **Configure Settings**:
    Use the bundled `config/settings.py` (for the standalone project) or your own Django settings module; ensure `audit_trail` plus its dependencies are installed.

    ```python
    # tests/settings.py or your local settings
    INSTALLED_APPS = [
        # ...
        "audit_trail",
        "tests", # Assuming you have a test app
    ]

    # Use Console Backend for local testing to see output in terminal
    AUDITTRAIL_STORAGE_BACKEND = "audit_trail.storage.backends.base.ConsoleStorageBackend" # You might need to implement this or use a mock
    # OR use DynamoDB Local / Mongo Local
    ```

    Environment variables (e.g., `DATABASE_URL`, `CELERY_BROKER_URL`, `AUDITTRAIL_USE_CELERY`) are read automatically by `config/settings.py`, so you can flip between inline and async delivery without editing Python files.

3.  **Run Migrations**:
    ```bash
    python manage.py migrate
    ```

## 2. Create Dummy Data & Trigger Events

You can use the Django shell to create data and trigger audit events.

1.  **Open Shell**:
    ```bash
    python manage.py shell
    ```

2.  **Run the following script**:

    ```python
    from django.conf import settings
    from audit_trail.registry import register_model
    from audit_trail.diffengine.mixins import AuditableMixin
    from django.db import models

    # 1. Define a Dummy Model (if not already in a real app)
    # Note: In a real shell, you can't define models dynamically easily without app registry.
    # Better to use an existing model in your 'tests' app or main app.
    # Assuming 'tests.TestModel' exists:

    # from tests.models import TestModel
    # register_model("tests.TestModel", fields=["name", "status"], sensitive=["secret"])

    # 2. Create an Instance (Triggers 'created' event)
    # obj = TestModel.objects.create(name="Test Policy", status="draft", secret="hidden123")
    # print(f"Created object: {obj.pk}")

    # 3. Update the Instance (Triggers 'updated' event)
    # obj.status = "active"
    # obj.save()
    # print("Updated object status")

    # 4. Check Outbox
    from audit_trail.storage.outbox.models import AuditEventOutbox
    print(f"Outbox entries: {AuditEventOutbox.objects.count()}")
    for entry in AuditEventOutbox.objects.all():
        print(f"[{entry.status}] {entry.event_type}: {entry.payload}")
    ```

## 3. Process the Outbox

Since we are using the Transactional Outbox pattern, events are initially stored in the `audit_trail_outbox` table. You need to run the worker or backfill command to process them.

**Option A: Run Celery Worker**
```bash
celery -A config worker -l info
```

**Option B: Synchronous Backfill (Easier for debugging)**
```bash
python manage.py audittrail_backfill --batch 10
```

> Tip: Set `AUDITTRAIL_USE_CELERY=False` (environment variable or inside `config/settings.py`) to automatically drain the outbox after each commit without running Celery—perfect for demos and smoke tests.

## 4. Verify Storage

After processing, check your configured storage backend.

-   **DynamoDB**: Check the AWS Console or use AWS CLI.
-   **MongoDB**: Use Compass or Mongo Shell.
-   **Console**: If you implemented a console backend, check stdout.

## 5. Verify UI

1.  **Run Server**:
    ```bash
    python manage.py runserver
    ```

2.  **Visit UI**:
    Navigate to `http://localhost:8000/` to see the navy blue login screen (“Welcome to Audit Trail vX.Y.Z”). After authenticating you will be redirected automatically to `http://localhost:8000/timeline/`, where the HTMX timeline renders.

## Troubleshooting

-   **No events in Outbox?**
    -   Did you register the model? `register_model(...)`
    -   Did you inherit `AuditableMixin`?
    -   Did you `save()` the object?

-   **Events stuck in 'pending'?**
    -   Is the Celery worker running?
    -   Did you run `audittrail_backfill`?

-   **Events in 'dlq'?**
    -   Check `last_error` field on the `AuditEventOutbox`.
    -   Verify storage credentials/connectivity.
