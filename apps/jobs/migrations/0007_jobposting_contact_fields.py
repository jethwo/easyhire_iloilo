from django.db import migrations, models

from apps.core.migration_helpers import add_column


def _add_contact_fields(apps, schema_editor):
    add_column(schema_editor, 'job_postings', 'contact_email',   'VARCHAR(254)')
    add_column(schema_editor, 'job_postings', 'contact_phone',   'VARCHAR(20)')
    add_column(schema_editor, 'job_postings', 'search_keywords', 'VARCHAR(500)')


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0006_alter_jobeducationrequirement_job'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # The columns already exist in the database from a prior schema —
            # we just need to register them in Django's model state.
            state_operations=[
                migrations.AddField(
                    model_name='jobposting',
                    name='contact_email',
                    field=models.EmailField(blank=True, default='', max_length=254),
                ),
                migrations.AddField(
                    model_name='jobposting',
                    name='contact_phone',
                    field=models.CharField(blank=True, default='', max_length=20),
                ),
                migrations.AddField(
                    model_name='jobposting',
                    name='search_keywords',
                    field=models.CharField(blank=True, default='', max_length=500),
                ),
            ],
            # Backfill nulls and set defaults so subsequent inserts succeed
            database_operations=[
                migrations.RunPython(_add_contact_fields, migrations.RunPython.noop),
            ],
        ),
    ]
