from django.db import migrations, models

from apps.core.migration_helpers import add_column


def _add_sector_badge_visibility(apps, schema_editor):
    add_column(schema_editor, 'jobseeker_profiles', 'sector_badge_visibility',
               'VARCHAR(20)', default='public')


class Migration(migrations.Migration):

    dependencies = [
        ('jobseekers', '0006_jobseekerprofile_profile_visibility'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='jobseekerprofile',
                    name='sector_badge_visibility',
                    field=models.CharField(default='public', max_length=20),
                ),
            ],
            database_operations=[
                migrations.RunPython(_add_sector_badge_visibility, migrations.RunPython.noop),
            ],
        ),
    ]
