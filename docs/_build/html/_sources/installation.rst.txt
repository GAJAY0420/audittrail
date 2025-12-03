Installation
============

1. Install package
------------------

.. code-block:: bash

   pip install tiger_audit_trail

2. Configure Django
-------------------

.. code-block:: python

   INSTALLED_APPS = [
       # ...
       "audit_trail",
   ]

3. Migrate
----------

.. code-block:: bash

   python manage.py migrate

4. Start Celery worker (package mode)
-------------------------------------

.. code-block:: bash

   celery -A your_project worker -l info

5. Standalone service mode
--------------------------

Clone the repository, configure the bundled project, and run it directly:

.. code-block:: bash

   export AUDITTRAIL_USE_CELERY=False  # optional eager processing for dev
   python manage.py migrate
   python manage.py runserver

When you are ready to scale beyond the inline dispatcher, switch the setting
back to ``True`` and run ``celery -A config worker -l info`` to drain the
outbox asynchronously.
