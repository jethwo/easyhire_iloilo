# EasyHire Iloilo

A job-matching platform for PESO Iloilo City. Jobseekers build a résumé,
employers post vacancies, and a matching engine scores the two against each
other; PESO staff review employers and job postings through an admin panel.

Django 5.1 · Python 3.12 · PostgreSQL or MariaDB/MySQL

---

## Setting up a local copy

**No accounts ship with this repository.** You create your own admin during
setup, and the demo jobseekers and employers are generated locally by a
management command. Nothing here is a shared credential.

### 1. Prerequisites

- **Python 3.12** — the project is pinned to 3.12 (`.python-version`).
  Newer versions may work but are untested.
- **A database server**, either:
  - PostgreSQL 13+ (the default), or
  - MariaDB 10.5+ / MySQL 8.0.11+ — see [DATABASE.md](DATABASE.md)

### 2. Virtual environment

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

On macOS/Linux: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`

The install pulls PyTorch and sentence-transformers for the matching engine,
so expect it to take a few minutes and about 2 GB.

### 3. Create an empty database

PostgreSQL:

```powershell
createdb -U postgres easyhire
```

MariaDB / MySQL:

```powershell
mysql -u root -p -e "CREATE DATABASE easyhire CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

### 4. Configure `.env`

Copy the template and fill it in:

```powershell
Copy-Item .env.example .env
```

At minimum set:

- **`DEBUG=True`** — required for local development. It defaults to `False`
  when unset, and the comparison is case-sensitive (`true` and `1` both
  read as False). With `DEBUG` off and no `DATABASE_URL`, settings.py
  assumes it is running in production and refuses to start with a message
  about Render.
- **`SECRET_KEY`** and **`DB_PASSWORD`**.
- **`DB_ENGINE`** plus the `MYSQL_DB_*` block, if you are not using
  PostgreSQL.

Generate a secret key with:

```powershell
.venv\Scripts\python.exe -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

`.env` is gitignored. Keep it that way — it holds your database and email
passwords.

### 5. Build the schema

```powershell
.venv\Scripts\python.exe manage.py migrate
```

**On MariaDB/MySQL only**, also load the time zone tables, or the analytics
charts will render empty with no error:

```powershell
.venv\Scripts\python.exe manage.py load_mysql_timezones
```

### 6. Load data

```powershell
.venv\Scripts\python.exe manage.py load_psgc
```

That loads Iloilo's 1,901 barangays from the bundled PSGC datafile — the
address pickers need it. Then, for a usable development dataset:

```powershell
.venv\Scripts\python.exe manage.py seed_demo
```

20 jobseekers with filled-in résumés, 10 companies, job postings,
applications and inbox content. Every seeded account uses the password
`easyhire2001`; those accounts exist only in your local database.

### 7. Create your own admin

```powershell
.venv\Scripts\python.exe manage.py createsuperuser
```

It prompts for an email and password — pick your own, and do not reuse the
seed password. `seed_demo` deliberately creates no staff accounts, so this
is the only way in to the admin panel.

### 8. Run it

```powershell
.\run.bat
```

`run.bat` uses `.venv` and falls back to `python` on PATH. Or directly:

```powershell
.venv\Scripts\python.exe manage.py runserver
```

| Surface | URL |
|---|---|
| Jobseeker / public site | http://127.0.0.1:8000/ |
| Employer portal | http://127.0.0.1:8000/employers/ |
| PESO admin panel | http://127.0.0.1:8000/admin-panel/login/ |

---

## Switching database backends

`DB_ENGINE` in `.env` selects PostgreSQL or MariaDB/MySQL, and a shell
variable overrides it for a single terminal:

```powershell
$env:DB_ENGINE = "mysql"; .\run.bat
```

The two databases are entirely separate — different accounts, different
data. [DATABASE.md](DATABASE.md) covers supported versions, moving data
between them, and the handful of behaviours that differ.

---

## Tests

```powershell
.venv\Scripts\python.exe manage.py test apps.core
```

These replay every migration into a fresh database and assert the schema is
correct on whichever backend is configured. Worth running on both before
changing anything migration-related.

---

## Project layout

| Path | Contents |
|---|---|
| `apps/accounts` | Custom user model (email login), allauth adapters |
| `apps/jobseekers` | Profiles, résumés, skills, NLP service |
| `apps/employers` | Companies, representatives, verification, candidate views |
| `apps/jobs` | Job postings, applications, hire flow |
| `apps/matching` | Compatibility scoring engine |
| `apps/notifications` | Bell notifications and transactional email |
| `apps/admin_panel` | PESO staff tooling, site settings, reports, announcements |
| `apps/analytics` | Dashboards and monthly reporting |
| `apps/core` | Shared models, inbox, PSGC geography, migration helpers |

---

## Notes for contributors

- **Never commit `.env` or a database dump.** Both are gitignored. Secrets
  that reach git history stay there even after the file is deleted.
- Seed data is regenerated, not shared. If you need a specific dataset,
  write or extend a seed command rather than committing a dump.
- The migrations under `apps/jobs` and `apps/jobseekers` numbered 0006–0008
  add columns through `apps/core/migration_helpers.py` so they work on both
  backends. Keep their filenames stable — databases that already applied
  them track them by name.
