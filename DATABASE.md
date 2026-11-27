# Database backends

EasyHire runs on **PostgreSQL** (the default) or on **MySQL / MariaDB**.
Pick one with `DB_ENGINE` in `.env`; nothing else in the codebase needs to
change.

```ini
DB_ENGINE=postgresql    # or: mysql / mariadb / postgres
DB_NAME=easyhire
DB_USER=postgres        # 'root' is the default when DB_ENGINE=mysql
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432            # omit to use the backend default (5432 / 3306)
```

Both servers can be configured at the same time. When `DB_ENGINE` selects
MySQL/MariaDB, any `MYSQL_DB_*` key takes precedence over its plain `DB_*`
counterpart, so the PostgreSQL credentials stay in place and switching is a
one-line change:

```ini
DB_ENGINE=mysql
MYSQL_DB_NAME=easyhire
MYSQL_DB_USER=root
MYSQL_DB_PASSWORD=...
MYSQL_DB_PORT=3306
```

## Supported versions

Taken from Django 5.1's own backend requirements:

| Backend | Minimum |
|---|---|
| PostgreSQL | 13+ |
| MySQL | 8.0.11 |
| MariaDB | 10.5 |

**MariaDB is the easier of the two** and the recommended choice. MySQL 8
rejects `ADD COLUMN IF NOT EXISTS` and refuses to put a `DEFAULT` on a
`TEXT` column; the migrations no longer rely on either, but MariaDB is more
forgiving if further raw SQL ever gets added.

The driver comes from `requirements.txt` (`mysqlclient`), which ships a
prebuilt wheel for Windows + Python 3.12 — no compiler needed.

## Switching to MySQL / MariaDB

1. **Install the server** and create an empty database:

   ```sql
   CREATE DATABASE easyhire CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
   ```

2. **Load the time zone tables.** This is not optional. The project runs
   with `USE_TZ = True`, and the analytics page uses `TruncMonth`, which
   Django compiles to `CONVERT_TZ()` on MySQL. Without the tz tables that
   function returns `NULL`, so the monthly charts come back empty **with no
   error**:

   ```bash
   python manage.py load_mysql_timezones
   ```

   This reads the TZif files from the `tzdata` package already in the
   virtualenv, so it needs no download and no system zoneinfo tree. It
   loads `UTC` and `settings.TIME_ZONE` by default (`--all` for every
   zone) and verifies `CONVERT_TZ` resolves before it finishes.

   The usual advice is `mysql_tzinfo_to_sql /usr/share/zoneinfo`, which
   does not work on Windows — there is no system zoneinfo tree, and
   MariaDB's bundled converter cannot walk one it is pointed at. Hence the
   management command.

3. **Point `.env` at it**: add the `MYSQL_DB_*` block above, then flip
   `DB_ENGINE=mysql`. Switching back is the same one line.

4. **Build the schema and load data:**

   ```bash
   python manage.py migrate
   python manage.py load_psgc        # 1,901 barangays of reference data
   python manage.py seed_demo        # demo companies, jobseekers, jobs
   ```

5. **Verify:**

   ```bash
   python manage.py test apps.core
   ```

   Those tests replay every migration into a fresh database and assert the
   columns the hand-written migrations create actually exist, that the
   `JSONField` round-trips, and that timezone-aware truncation returns a
   real value rather than `NULL`. If step 2 was skipped, the last one fails
   and tells you so.

## Moving existing data across

`pg_dump` output cannot be fed to MySQL. Either re-seed from scratch (steps
4 above — the database is mostly reference and demo data), or go through
Django:

```bash
# on PostgreSQL
python manage.py dumpdata --natural-primary --natural-foreign \
    -e contenttypes -e auth.Permission -e sessions -e admin.logentry \
    --indent 2 -o data.json

# then with .env pointed at MySQL
python manage.py migrate
python manage.py loaddata data.json
```

The exclusions matter: content types and permissions are recreated by
`migrate`, and loading the old rows on top causes integrity errors.

## Behaviour that differs between the two

None of these is a bug, but each will surprise you.

### Two uniqueness guarantees are lost

`manage.py check --database default` reports this on MySQL/MariaDB:

```
account.EmailAddress: (models.W036) MariaDB does not support unique
constraints with conditions.  HINT: A constraint won't be created.
```

It fires twice, for django-allauth's two *conditional* unique constraints:

| Constraint | Guarantees |
|---|---|
| `unique_primary_email` | one primary email address per user |
| `unique_verified_email` | a verified email address is globally unique |

PostgreSQL enforces both as partial unique indexes. **MySQL and MariaDB
support neither, so they are silently skipped** — confirmed by inspecting
`account_emailaddress`, which ends up with only the `(user_id, email)`
unique index and a plain index on `email`.

allauth also enforces both rules in application code, so ordinary signup
and email-management flows behave the same. What is gone is the database's
safety net against a race between two concurrent requests, or against code
that writes `EmailAddress` rows directly through the ORM. If that matters,
the usual workaround is a `STORED` generated column (`IF(verified, email,
NULL)`) with a unique index on it, since NULLs do not collide — MariaDB
10.2+ supports this.

### `mysql.W003` on `Company.slug` is a false alarm here

```
employers.Company.slug: (mysql.W003) MariaDB may not allow unique
CharFields to have a max_length > 255.
```

The warning is generic; in this schema the index is fine. `slug` is 300
characters, which under `utf8mb4` is 1,200 bytes — well inside InnoDB's
3,072-byte key limit with the `DYNAMIC` row format MariaDB has defaulted to
since 10.2. `SHOW INDEX FROM companies` confirms a full-column unique index
with no prefix truncation. No other indexed column in the schema exceeds
768 characters.

### Case sensitivity flips

MySQL and MariaDB default to a case-*insensitive* collation
(`utf8mb4_unicode_ci` here). `filter(email='A@x.com')` matches `a@x.com`,
and the unique index on `Company.slug` treats `Acme` and `acme` as the same
value — PostgreSQL allows both rows. The `email__iexact` lookups in
`apps/accounts` become redundant but stay correct.

### DDL is not transactional

A migration that fails halfway leaves the schema partly changed;
PostgreSQL rolls the whole migration back. Take a dump before migrating a
database you care about.

### One column default differs

`applications.application_message` carries a SQL default of `''` on
PostgreSQL and none on MySQL/MariaDB, because MySQL forbids defaults on
`TEXT` columns. This is deliberate and has no effect: Django always sends
an explicit value and never depends on a database-level default. The column
is nullable and backfilled on both.

## Verified on both backends

As of the `mysql-migration` branch, both of these pass:

```bash
python manage.py test apps.core                   # PostgreSQL
DB_ENGINE=mysql python manage.py test apps.core   # MariaDB
```

All 83 migrations replay from zero on MariaDB 13.1.2 (67 tables), the seven
columns the hand-written migrations add are present with the right types,
and the four application features — employer recommendation scope,
invitations in the inbox, the 1,000-character message cap, and the admin
settings lock — were exercised end to end against both databases.

## How the migrations stay portable

Five early migrations add columns with raw SQL
(`apps/jobs/migrations/0007`, `0008`, and `apps/jobseekers/migrations/0006`,
`0007`, `0008`). They use `SeparateDatabaseAndState` because the columns
already existed in an older deployment — but on a fresh database that raw
SQL is what creates them.

That SQL was PostgreSQL-only. It now goes through
`apps/core/migration_helpers.py`, which checks `information_schema` for the
column and emits backend-appropriate DDL. The migration *names* are
unchanged, so databases that already applied them do not re-run anything.
