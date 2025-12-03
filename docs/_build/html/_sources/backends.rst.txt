Storage Backends
================

DynamoDB
--------
- Strong consistency via PK ``object_id`` + SK ``timestamp``.
- Recommended for high write throughput.
- Implements ``fetch_object_events`` via the ``object_id/timestamp`` GSI and
	``fetch_user_events`` through the ``user_id/timestamp`` GSI powering the
	history service.

MongoDB
-------
- Flexible document model; ideal when embedding custom metadata.
- Index on ``object_id`` and ``timestamp`` for timeline queries.
- ``fetch_object_events`` sorts by the ``_id`` cursor, while
	``fetch_user_events`` reuses the shared ``user_id`` index for consistent
	pagination in the history browser.

S3
---
- Cost-optimized cold storage.
- Files partitioned by ``YYYY/MM/DD`` for Athena/Glue querying.
- Server-side encryption enforced (AES-256).
- History retrieval lists JSON artifacts under per-object and per-user prefixes
	(``object/<app.Model>/<pk>/`` or ``user/<id>/``) before loading payloads into
	``HistoryEvent`` objects.
