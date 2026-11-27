from django.db import migrations, models

from apps.core.migration_helpers import add_column


def _add_profile_picture(apps, schema_editor):
    add_column(schema_editor, 'jobseeker_profiles', 'profile_picture',
               'VARCHAR(100)', default=None)


class Migration(migrations.Migration):

    dependencies = [
        ('jobseekers', '0007_jobseekerprofile_sector_badge_visibility'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # The column already exists in the DB (added previously). Just
            # update Django's model state so the ORM knows about the field.
            state_operations=[
                migrations.AddField(
                    model_name='jobseekerprofile',
                    name='profile_picture',
                    field=models.ImageField(blank=True, null=True, upload_to='profile_pictures/'),
                ),
            ],
            database_operations=[
                migrations.RunPython(_add_profile_picture, migrations.RunPython.noop),
            ],
        ),
    ]
