from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0010_id_verification_notif_types'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notif_type',
            field=models.CharField(choices=[('company_liked_you', 'Company Liked You'), ('jobseekers_liked_job', 'Jobseekers Liked Job'), ('match', 'Match'), ('job_deleted_by_admin', 'Job Deleted by Admin'), ('job_approved', 'Job Post Approved'), ('job_rejected', 'Job Post Rejected'), ('personal_info_approved', 'Personal Info Change Approved'), ('personal_info_rejected', 'Personal Info Change Rejected'), ('id_verification_approved', 'ID Verification Approved'), ('id_verification_denied', 'ID Verification Denied'), ('new_application', 'New Job Application'), ('application_accepted', 'Application Accepted'), ('application_rejected', 'Application Rejected'), ('application_hired', 'Application Hired'), ('employer_contacted', 'Employer Sent Contact'), ('invited_to_apply', 'Invited to Apply'), ('hire_offered', 'Hire Offered'), ('hire_accepted', 'Hire Accepted'), ('hire_declined', 'Hire Declined'), ('application_unhired', 'Application Un-hired'), ('new_announcement', 'New PESO Announcement')], max_length=30),
        ),
    ]
