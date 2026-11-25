from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def approve_existing_jobs(apps, schema_editor):
    """Everything that existed before the approval gate was already live on
    the site, so grandfather it in as approved. Without this every current
    posting would silently drop off the public listings the moment this
    migration runs.
    """
    JobPosting = apps.get_model("jobs", "JobPosting")
    JobPosting.objects.all().update(approval_status="approved")


def unapprove_all(apps, schema_editor):
    """Reverse of the back-fill — nothing to restore, the columns go away."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("jobs", "0019_alter_jobeducationrequirement_level"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobposting",
            name="approval_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Approval"),
                    ("approved", "Approved"),
                    ("rejected", "Rejected"),
                ],
                default="pending",
                help_text="Jobs are only published to jobseekers once a PESO admin approves them.",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="jobposting",
            name="approval_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="jobposting",
            name="submitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobposting",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobposting",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="job_approvals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(approve_existing_jobs, unapprove_all),
    ]
