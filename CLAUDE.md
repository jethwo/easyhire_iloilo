# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

# Project: EasyHire Iloilo (OJT)

Job-matching web app: jobseekers upload résumés, and a matching engine scores jobs against them.

## Tech stack

**Backend**
- Python 3.12, Django 5.0–5.1. Use Django's built-in session login and admin.
- django-allauth for accounts and Google sign-in (PyJWT for the Google part).
- hashids for scrambled IDs in URLs. Never expose raw database IDs in URLs.
- Pillow and pillow-heif for image uploads (including iPhone HEIC photos).
- python-dotenv for settings in `.env`; dj-database-url for database URLs.

**Database**
- PostgreSQL by default, or MySQL/MariaDB via the `DB_ENGINE` setting (psycopg2, mysqlclient).
- Keep queries and migrations compatible with both PostgreSQL and MySQL/MariaDB.

**Matching and résumé parsing**
- Custom matching engine in `apps/matching` that scores jobs against jobseekers.
- sentence-transformers on CPU-only PyTorch for skill similarity.
- rapidfuzz for fuzzy text matching.
- pdfplumber for reading uploaded PDF résumés.
- tesseract.js for OCR of uploaded images, running in the browser.

**Frontend**
- Django templates with Tailwind CSS from the CDN, plus our own `public.css` for the new theme.
- Plain JavaScript only. No front-end framework and no build step.
- Inter font (Google Fonts), Chart.js for analytics charts, Cropper.js for profile-photo cropping.

**Files and hosting**
- WhiteNoise for static files; Cloudinary (cloudinary, django-cloudinary-storage) for uploaded media.
- Gunicorn in production, deployed on Render.
- SMTP for email in production.

## Do not use

These are listed in `requirements.txt` but are NOT used in the code. Do not import them or build on them unless asked:
Celery, Redis, Django Channels, django-htmx, django-crispy-forms, spaCy, django-debug-toolbar.
`apps/messaging` is not wired to WebSockets.

## Commands

- Run server: `python manage.py runserver`
- Migrations: `python manage.py makemigrations` then `python manage.py migrate`
- Tests: `python manage.py test`

## Rules for this project

- Never commit `.env` or secrets. Settings come from environment variables.
- Don't edit existing migrations that have already been applied; add a new one.
- Match the existing template and CSS style. Use Tailwind classes and `public.css`; don't add a new CSS framework.
- Don't add new dependencies without asking first.