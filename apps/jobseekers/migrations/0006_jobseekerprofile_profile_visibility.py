from django.db import migrations, models

from apps.core.migration_helpers import add_column


def _add_profile_visibility(apps, schema_editor):
    add_column(schema_editor, 'jobseeker_profiles', 'profile_visibility',
               'VARCHAR(20)', default='public')


class Migration(migrations.Migration):

    dependencies = [
        ('jobseekers', '0005_jobseekerprofile_bio'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # Tell Django's ORM that this field exists (model state update only)
            state_operations=[
                migrations.AddField(
                    model_name='jobseekerprofile',
                    name='profile_visibility',
                    field=models.CharField(default='public', max_length=20),
                ),
            ],
            # Column already exists in the DB — just backfill nulls and set a default
            database_operations=[
                migrations.RunPython(_add_profile_visibility, migrations.RunPython.noop),
            ],
        ),
    ]
