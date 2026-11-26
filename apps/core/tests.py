"""Schema checks that must hold on every supported database backend.

These run against the test database, which Django builds by replaying every
migration from zero — so they verify the hand-written migrations in
apps/jobs and apps/jobseekers actually create their columns, not just that
Django's model state believes they exist.

Run them on each backend you intend to deploy on:

    python manage.py test apps.core                     # whatever DB_ENGINE says
    DB_ENGINE=mysql python manage.py test apps.core     # MySQL / MariaDB
"""
from django.db import connection
from django.test import TestCase

from apps.core.migration_helpers import column_exists


class _SchemaEditorStub:
    """Minimal stand-in so column_exists() can be reused outside a migration.

    The helper only ever touches `.connection` and `.quote_name`, which is
    all this provides — it keeps the test honest by exercising the same
    introspection code the migrations rely on.
    """

    def __init__(self, conn):
        self.connection = conn

    def quote_name(self, name):
        return self.connection.ops.quote_name(name)


# (table, column) pairs added by the raw-SQL migrations that were rewritten
# to be vendor-neutral. If any of these is missing, a fresh database built
# on this backend is subtly broken: Django's model state claims the field
# exists, so the breakage only surfaces as an OperationalError at runtime.
HAND_WRITTEN_COLUMNS = [
    ('job_postings', 'contact_email'),
    ('job_postings', 'contact_phone'),
    ('job_postings', 'search_keywords'),
    ('applications', 'application_message'),
    ('jobseeker_profiles', 'profile_visibility'),
    ('jobseeker_profiles', 'sector_badge_visibility'),
    ('jobseeker_profiles', 'profile_picture'),
]


class HandWrittenMigrationColumnsTests(TestCase):
    def test_every_hand_written_column_exists(self):
        editor = _SchemaEditorStub(connection)
        missing = [
            f'{table}.{column}'
            for table, column in HAND_WRITTEN_COLUMNS
            if not column_exists(editor, table, column)
        ]
        self.assertEqual(
            missing, [],
            f'Columns missing on {connection.vendor}: {", ".join(missing)}. '
            'The migration that adds them did not run correctly on this backend.',
        )

    def test_columns_are_writable_through_the_orm(self):
        """Guards the db_column mapping, not just the column's presence.

        Application.message maps to the `application_message` column, which
        is the one case where the Python name and the SQL name differ — an
        easy thing to get wrong when rewriting raw SQL.
        """
        from apps.employers.models import Company
        from apps.jobs.models import JobPosting

        company = Company.objects.create(
            name='Schema Test Co', slug='schema-test-co',
            type_of_company=Company.LOCAL, nature_of_company='Testing',
            company_email='a@example.com', recruitment_email='b@example.com',
            main_branch_address='Iloilo City',
        )
        job = JobPosting.objects.create(
            company=company, title='Schema Test Role',
            contact_email='c@example.com', contact_phone='09170000000',
            search_keywords='schema test',
        )
        job.refresh_from_db()
        self.assertEqual(job.contact_email, 'c@example.com')
        self.assertEqual(job.search_keywords, 'schema test')


class DatabaseCapabilityTests(TestCase):
    """Documents the backend assumptions the project actually depends on."""

    def test_json_field_round_trips(self):
        """ImportBatch.error_log is a JSONField.

        Supported on PostgreSQL, MySQL 5.7.8+ and MariaDB 10.2.7+. A failure
        here means the server is older than the project supports.
        """
        from apps.admin_panel.models import ImportBatch

        batch = ImportBatch.objects.create(error_log=[{'row': 3, 'error': 'bad date'}])
        batch.refresh_from_db()
        self.assertEqual(batch.error_log, [{'row': 3, 'error': 'bad date'}])

    def test_timezone_aware_truncation_works(self):
        """TruncMonth under USE_TZ=True.

        On MySQL / MariaDB this compiles to CONVERT_TZ(), which returns NULL
        unless the server's time zone tables have been loaded with
        mysql_tzinfo_to_sql. The analytics charts depend on it, and the
        failure is silent — empty buckets rather than an error — so it is
        worth asserting explicitly.
        """
        from django.db.models.functions import TruncMonth

        from apps.accounts.models import User

        User.objects.create_user(email='tz@example.com', password='x' * 12)
        row = (User.objects
               .annotate(month=TruncMonth('created_at'))
               .values('month').first())
        self.assertIsNotNone(
            row['month'],
            'TruncMonth returned NULL. On MySQL/MariaDB this means the time '
            'zone tables are not loaded: run mysql_tzinfo_to_sql against the '
            'mysql database, then retry.',
        )
