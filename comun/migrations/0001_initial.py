from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="EventoProcesado",
            fields=[
                ("event_id", models.UUIDField(primary_key=True, serialize=False)),
                ("event", models.CharField(max_length=100)),
                ("source", models.CharField(blank=True, max_length=50)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "evento_procesado"},
        ),
    ]
