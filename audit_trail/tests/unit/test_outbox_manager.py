import pytest

from audit_trail.storage.outbox.models import AuditEventOutbox


@pytest.mark.django_db
def test_enqueue_and_acquire(django_user_model):
    entry = AuditEventOutbox.objects.create(
        model_label="app.Model",
        object_pk="1",
        payload={"foo": "bar"},
        context={},
    )
    batch = list(AuditEventOutbox.objects.acquire_batch(batch_size=1))
    assert len(batch) == 1
    assert batch[0].id == entry.id
