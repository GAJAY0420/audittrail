from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Address",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("label", models.CharField(max_length=128)),
            ],
            options={"app_label": "testapp"},
        ),
        migrations.CreateModel(
            name="BusinessPartnerRole",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=64)),
            ],
            options={"app_label": "testapp"},
        ),
        migrations.CreateModel(
            name="BusinessPartner",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("first_name", models.CharField(max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "addresses",
                    models.ManyToManyField(
                        blank=True,
                        related_name="partners",
                        through="testapp.UserAddress",
                        to="testapp.address",
                    ),
                ),
                (
                    "roles",
                    models.ManyToManyField(
                        blank=True,
                        related_name="partners",
                        to="testapp.businesspartnerrole",
                    ),
                ),
            ],
            options={"app_label": "testapp"},
        ),
        migrations.CreateModel(
            name="UserAddress",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("nickname", models.CharField(blank=True, max_length=64)),
                (
                    "address",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        to="testapp.address",
                    ),
                ),
                (
                    "partner",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        to="testapp.businesspartner",
                    ),
                ),
            ],
            options={
                "app_label": "testapp",
                "unique_together": {("partner", "address")},
            },
        ),
    ]
