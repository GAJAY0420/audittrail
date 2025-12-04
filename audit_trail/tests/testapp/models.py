from __future__ import annotations

from django.db import models


class BusinessPartnerRole(models.Model):
    name = models.CharField(max_length=64)

    class Meta:
        app_label = "testapp"

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return self.name


class Address(models.Model):
    label = models.CharField(max_length=128)

    class Meta:
        app_label = "testapp"

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return self.label


class BusinessPartner(models.Model):
    first_name = models.CharField(max_length=64)
    roles = models.ManyToManyField(
        BusinessPartnerRole,
        blank=True,
        related_name="partners",
    )
    addresses = models.ManyToManyField(
        Address,
        through="UserAddress",
        related_name="partners",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "testapp"

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return self.first_name


class UserAddress(models.Model):
    partner = models.ForeignKey(BusinessPartner, on_delete=models.CASCADE)
    address = models.ForeignKey(Address, on_delete=models.CASCADE)
    nickname = models.CharField(max_length=64, blank=True)

    class Meta:
        app_label = "testapp"
        unique_together = ("partner", "address")

    def __str__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.partner_id}:{self.address_id}"
