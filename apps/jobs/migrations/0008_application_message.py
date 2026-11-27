from django.db import migrations, models

from apps.core.migration_helpers import add_column


def _add_application_message(apps, schema_editor):
    # TEXT, so no SQL default is installed on MySQL - see add_column().
    add_column(schema_editor, 'applications', 'application_message', 'TEXT')


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0007_jobposting_contact_fields'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='application',
                    name='message',
                    field=models.TextField(blank=True, default='', db_column='application_message'),
                ),
            ],
            database_operations=[
                migrations.RunPython(_add_application_message, migrations.RunPython.noop),
            ],
        ),
    ]
