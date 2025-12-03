API Reference
=============

AuditEventViewSet
-----------------

.. autoclass:: audit_trail.api.views.AuditEventViewSet
   :members:

History Service
---------------

.. autofunction:: audit_trail.history.service.fetch_history

.. autoclass:: audit_trail.history.service.HistoryResult
   :members:

.. autoclass:: audit_trail.history.service.HistoryEvent
   :members:

.. autoclass:: audit_trail.history.service.HistoryQueryError

UI Helpers
----------

.. autoclass:: audit_trail.ui.forms.HistorySearchForm
   :members:

.. autoclass:: audit_trail.ui.views.HistorySearchView
   :members:

Sensitive Utilities
-------------------

.. autofunction:: audit_trail.utils.sensitive.unmask_change

Management Commands
-------------------

- ``audittrail_backfill``
- ``audittrail_replay``
- ``audittrail_clean``
- ``audittrail_stats``
