# tiger_audit_trail

Enterprise-grade audit logging for Django featuring diff capture, transactional outbox delivery, multi-backend storage (DynamoDB/MongoDB/S3), optional Kafka/Kinesis streaming, and HTMX-powered timelines.

> Requires Python 3.13+ and Django 5.2+.

## Why Audit Trail?
- **Transactional safety** – Outbox table lives in the same database transaction as business data.
- **Async scaling** – Celery workers batch events to downstream stores.
- **Extensible storage** – Pluggable adapters for DynamoDB, MongoDB, or S3.
- **Streaming ready** – Toggle Kafka or Kinesis streaming via settings.
- **Summaries** – Rule-based, NLTK, multilingual, or LLM summaries of diffs.

## Installation
Add to `requirements.txt`:

```text
git+https://github.com/your-org/tiger_audit_trail.git@main#egg=tiger_audit_trail
```

Install dependencies and apply migrations:

```bash
pip install -r requirements.txt
python manage.py migrate
```

## Django Configuration
```python
INSTALLED_APPS = [
    # ...
    "audit_trail",
]

AUDITTRAIL_STORAGE_BACKEND = "audit_trail.storage.backends.dynamo.DynamoStorageBackend"
AUDITTRAIL_STORAGE_CONFIG = {
    "table": "audit-events",
    "region": "us-east-1",
}

AUDITTRAIL_STREAMING_ENABLED = True
AUDITTRAIL_STREAM_PROVIDER = "audit_trail.streaming.kafka.KafkaPublisher"
AUDITTRAIL_STREAM_CONFIG = {
    "topic": "audit-events",
    "bootstrap_servers": "broker01:9092,broker02:9092",
}

# Inline processing for local-dev only (default True for async workers)
AUDITTRAIL_USE_CELERY = True

AUDITTRAIL_SUMMARIZER = "grammar"  # grammar|nltk|multilang|llm
AUDITTRAIL_ACTOR_RESOLVER = "auths.middleware.get_current_user"  # optional thread-local helper
AUDITTRAIL_SENSITIVE_KEY = os.environ["AUDIT_SENSITIVE_KEY"]  # AES-256 key for encrypted diffs

# LLM providers (choose one)
# OpenAI (Chat Completions)
AUDITTRAIL_SUMMARIZER = "llm"
AUDITTRAIL_LLM_PROVIDER = "openai"
AUDITTRAIL_LLM_MODEL = "gpt-4o-mini"
AUDITTRAIL_LLM_TOKEN = os.environ["OPENAI_API_KEY"]

# Claude (Anthropic)
# AUDITTRAIL_LLM_PROVIDER = "claude"
# AUDITTRAIL_LLM_MODEL = "claude-3-haiku-20240307"
# AUDITTRAIL_LLM_TOKEN = os.environ["ANTHROPIC_API_KEY"]

# Gemini (Google Generative AI)
# AUDITTRAIL_LLM_PROVIDER = "gemini"
# AUDITTRAIL_LLM_MODEL = "gemini-1.5-flash"
# AUDITTRAIL_LLM_TOKEN = os.environ["GEMINI_API_KEY"]

# AWS Bedrock (Bearer token flow)
# AUDITTRAIL_LLM_PROVIDER = "bedrock"
# AUDITTRAIL_LLM_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"
# AUDITTRAIL_BEDROCK_REGION = "eu-central-1"
# AUDITTRAIL_BEDROCK_ACCESS_KEY = os.environ["AWS_ACCESS_KEY_ID"]  # optional, prefer IAM roles
# AUDITTRAIL_BEDROCK_SECRET_KEY = os.environ["AWS_SECRET_ACCESS_KEY"]
# AUDITTRAIL_BEDROCK_SESSION_TOKEN = os.environ.get("AWS_SESSION_TOKEN", "")
# AUDITTRAIL_LLM_SYSTEM_PROMPT = "Summarize audit deltas for executives in German."
```

`AUDITTRAIL_ACTOR_RESOLVER` is a dotted path to a no-arg callable (for example a
thread-local helper exposed by your authentication middleware). When provided, the
callable is evaluated for every audit event and the returned user metadata is stored
as a dictionary—`{"username": "alice", "email": "alice@example.com", "id": 42}`.
The mixin automatically handles string, dict, or user-object results so you do not
need per-model overrides.

To inspect a sensitive diff in internal tooling, import
``audit_trail.utils.sensitive.unmask_change`` and pass the diff entry along with the
desired position (``"before"`` or ``"after"``). Only services that know
``AUDITTRAIL_SENSITIVE_KEY`` can decrypt the ciphertext, so external storage still
sees masked values.

### Diff Payload 101

Each audit event now carries a structured `diff` object alongside a `changes` alias to
keep older consumers happy. Scalar fields look like this:

```json
"status": {
    "field": "status",
    "field_type": "CharField",
    "relation": "field",
    "before": "pending",
    "after": "approved"
}
```

Foreign keys and one-to-one fields automatically resolve the related object so the
timeline and summaries remain human readable:

```json
"owner": {
    "field": "owner",
    "field_type": "ForeignKey",
    "relation": "foreign_key",
    "before": {"pk": 7, "repr": "Alice"},
    "after": {"pk": 9, "repr": "Bob"}
}
```

Many-to-many updates surface both additions and removals:

```json
"tags": {
    "field": "tags",
    "relation": "many_to_many",
    "added": [{"pk": 1, "repr": "Critical"}],
    "removed": [{"pk": 4, "repr": "Legacy"}]
}
```

The summarizers (grammar, nltk, multilang, LLM) consume this rich payload to produce
plain-English (or localized) sentences without dumping JSON blobs, so every UI card
and streaming consumer gets a single, readable summary string out of the box.

## Registering Models
```python
# myapp/apps.py
from django.apps import AppConfig

from audit_trail.registry import register_model


class MyAppConfig(AppConfig):
    def ready(self):
        register_model(
            "policies.Policy",
            fields=["status", "premium"],
            sensitive=["ssn"],
            m2m=["risk_classes"],
        )
```

Attach the mixin for context enrichment:

```python
from audit_trail.diffengine.mixins import AuditableMixin


class Policy(AuditableMixin, models.Model):
    status = models.CharField(max_length=32)

    def get_audit_context(self):
        return {"actor": self.updated_by.username}
```

## Kafka Example (README)
```python
AUDITTRAIL_STREAMING_ENABLED = True
AUDITTRAIL_STREAM_PROVIDER = "audit_trail.streaming.kafka.KafkaPublisher"
AUDITTRAIL_STREAM_CONFIG = {
    "topic": "audit-events",
    "bootstrap_servers": "broker:9092",
    "security.protocol": "SASL_SSL",
    "sasl.mechanisms": "PLAIN",
}
```

Consumer snippet:

```python
from confluent_kafka import Consumer

consumer = Consumer({"bootstrap.servers": "broker:9092", "group.id": "audit"})
consumer.subscribe(["audit-events"])
while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue
    event = json.loads(msg.value())
    print(event["summary"])
```

## Kinesis Example (README)
```python
AUDITTRAIL_STREAMING_ENABLED = True
AUDITTRAIL_STREAM_PROVIDER = "audit_trail.streaming.kinesis.KinesisPublisher"
AUDITTRAIL_STREAM_CONFIG = {
    "stream": "audit-stream",
    "region": "us-east-1",
}
```

IAM policy snippet:

```json
{
  "Effect": "Allow",
  "Action": ["kinesis:PutRecord", "kinesis:DescribeStream"],
  "Resource": "arn:aws:kinesis:us-east-1:123456789012:stream/audit-stream"
}
```

## Operating the Outbox
- `celery -A project worker -l info` to run async dispatch.
- `python manage.py audittrail_backfill --batch 500` drains synchronously.
- `python manage.py audittrail_clean` purges sent entries & releases locks.
- `python manage.py audittrail_stats` prints counts per status.

## Standalone Execution & Dual Mode
- Clone the repo, install dependencies (`pip install -e .[dev]`), and run `python manage.py migrate` using the bundled `config/settings.py` project.
- Start the API + HTMX timeline via `python manage.py runserver` and visit `http://localhost:8000/timeline/` to browse audit history.
- Run `celery -A config worker -l info` (and optional beat) when `AUDITTRAIL_USE_CELERY=True` for full async delivery.
- Toggle `AUDITTRAIL_USE_CELERY=False` in `config/settings.py` or the environment to process the outbox inline—handy for demos/tests when you do not want Celery running.
- Configure `DATABASE_URL`, `CELERY_BROKER_URL`, and storage/streaming settings through environment variables to mirror production even while running in standalone mode.

## UI
- Visit `http://localhost:8000/` for the branded login (HTMX-enabled, navy theme) and you will be redirected to the timeline after authentication.
- Include the template tag in your URLs and render `audit_trail/ui/templates/audit_trail/history.html` to embed the HTMX timeline.

## Documentation
Full Sphinx docs live under `docs/`. Build via:

```bash
cd docs
make html
```

## Security Considerations
- **IAM only**: Boto clients rely on environment/instance profiles.
- **PII masking**: Fields listed in `sensitive` registry entries are hashed via SHA-256 before leaving Postgres.
- **RBAC**: API viewset enforces `audit_trail.view_audit_log` permission.
- **Encryption**: S3 adapter forces `AES256`, Kinesis/Kafka links should run over TLS.

## Development Tips
- Install and run the shared git hooks: `pip install pre-commit && pre-commit install`.
- Python 3.13 and Django 5.2 are the supported minimums; keep local environments aligned for parity with CI and Dependabot updates.

## License
MIT
