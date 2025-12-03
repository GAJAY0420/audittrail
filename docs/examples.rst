Examples
========

1. Policy model registration.
2. Masking sensitive SSN field.
3. Multilingual summary toggle.
4. HTMX timeline include.
5. Kafka streaming enable.
6. Kinesis streaming enable.
7. DynamoDB backend config.
8. MongoDB backend config.
9. S3 archival export toggle.
10. Celery beat schedule for dispatcher.

.. code-block:: python

   AUDITTRAIL_SUMMARIZER = "multilang"
   AUDITTRAIL_SUMMARIZER_LOCALE = "de"

.. code-block:: python

   CELERY_BEAT_SCHEDULE = {
       "dispatch-outbox": {
           "task": "audit_trail.tasks.dispatch_outbox",
           "schedule": 60.0,
           "args": (250,),
       }
   }

.. code-block:: python

   # Toggle eager dispatching for demos or test environments
   AUDITTRAIL_USE_CELERY = False

Structured Diff & Summary
-------------------------

When a model changes, each field produces a rich entry inside ``event["diff"]``:

.. code-block:: json

    {
       "status": {
          "field": "status",
          "field_type": "CharField",
          "relation": "field",
          "before": "pending",
          "after": "approved"
       },
       "tags": {
          "field": "tags",
          "relation": "many_to_many",
          "added": [{"pk": 1, "repr": "Critical"}],
          "removed": [{"pk": 4, "repr": "Legacy"}]
       }
    }

The grammar/nltk/multilang summarizers convert this into sentences such as:

.. code-block:: text

    Status (CharField) changed from pending to approved; Tags updated: added Critical, removed Legacy.

The timeline UI renders the same structure without showing raw JSON, making the
history feed approachable for non-technical reviewers.

Programmatic History Retrieval
------------------------------

The new ``audit_trail.history.service`` helper lets you query the configured
storage backend directly from a Django shell, management command, or Celery task.

.. code-block:: python

   from audit_trail.history import service

   # Fetch by object
   result = service.fetch_history(model="policies.Policy", object_id="42")
   for event in result.events:
      print(event.timestamp, event.summary, event.actor)

   # Page through user activity
   user_events = service.fetch_history(user_id="7", limit=50)
   print(f"Next cursor: {user_events.next_cursor}")

Inside the UI, ``HistorySearchForm`` validates the same inputs and
``HistorySearchView`` renders a Tailwind/HTMX feed powered by
``templates/audit_trail/history_search.html``.  Drop
``{% url 'audit-history-search' %}`` into your navbar to let operators explore
archived records without touching the API.
