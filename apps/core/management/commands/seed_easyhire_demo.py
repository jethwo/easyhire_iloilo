"""Seed 15 demo jobseekers and 10 demo companies (3-5 jobs each) whose jobs
match their industry, with full Iloilo City address data (street, barangay,
PSGC codes). Writes every login to demo_credentials.txt in the project root.

    python manage.py seed_easyhire_demo           # add data (idempotent)
    python manage.py seed_easyhire_demo --wipe    # remove the demo data first

Emails:  <name>@jobseeker.easyhire   /   <company>@employer.easyhire
Password for every account: easyhire2001
"""
import random
from datetime import date

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.core.models import Barangay, CityMunicipality
from apps.employers.models import Company, EmployerProfile
from apps.jobs.models import (
    JobCertificationRequirement, JobEducationRequirement,
    JobExperienceRequirement, JobPosting, JobSkillRequirement,
)
from apps.jobseekers.models import (
    Certification, Education, JobseekerProfile, Sector, Skill, WorkExperience,
)

from ._demo_data import (
    COMPANIES, JOBSEEKERS, PASSWORD, credentials_text, employer_email,
    jobseeker_email,
)

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


def _mark_email_verified(user, email):
    try:
        from allauth.account.models import EmailAddress
    except ImportError:
        return
    EmailAddress.objects.update_or_create(
        user=user, email=email, defaults={"verified": True, "primary": True},
    )


class Command(BaseCommand):
    help = "Seed 15 jobseekers and 10 companies with industry-matched jobs (password easyhire2001)."

    def add_arguments(self, parser):
        parser.add_argument("--wipe", action="store_true",
                            help="Delete the demo users/companies created by this command first.")

    # ── address helpers ────────────────────────────────────────────
    def _load_location(self):
        city = (CityMunicipality.objects.filter(code="063022000").first()
                or CityMunicipality.objects.filter(name__icontains="iloilo", province__name__icontains="iloilo")
                .exclude(name__icontains="province").first())
        self._city = city
        self._barangays = list(Barangay.objects.filter(city=city)) if city else []
        self._rng = random.Random(2001)
        if not self._barangays:
            self.stdout.write(self.style.WARNING(
                "No Iloilo City barangays found in the PSGC tables - barangay codes will be blank. "
                "Run `python manage.py load_psgc` first if you want codes filled in."))

    def _barangay(self, preferred):
        """Return (code, name). Match the preferred names against the PSGC table,
        else fall back to a real barangay of the city so the code is never blank."""
        for name in preferred:
            hit = next((b for b in self._barangays if b.name.lower() == name.lower()), None) \
                or next((b for b in self._barangays if name.lower() in b.name.lower()), None)
            if hit:
                return hit.code, hit.name
        if self._barangays:
            b = self._rng.choice(self._barangays)
            return b.code, b.name
        return "", preferred[0]

    def _codes(self):
        city = self._city
        if not city:
            return "063000000", ""
        return city.province.code, city.code

    # ── main ───────────────────────────────────────────────────────
    @transaction.atomic
    def handle(self, *args, **opts):
        rng = random.Random(42)
        self._load_location()
        province_code, city_code = self._codes()

        if opts["wipe"]:
            Company.objects.filter(slug__in=[c["slug"] for c in COMPANIES]).delete()
            emails = [employer_email(c) for c in COMPANIES] + [jobseeker_email(j) for j in JOBSEEKERS]
            n, _ = User.objects.filter(email__in=emails).delete()
            self.stdout.write(self.style.WARNING(f"Wiped existing demo data ({n} rows)."))

        sectors = {}
        for code, label in Sector.SECTOR_CHOICES:
            sectors[code], _ = Sector.objects.get_or_create(code=code, defaults={"label": label})

        now = timezone.now()
        today = date.today()

        # ── Companies, employer accounts, jobs ─────────────────────
        job_total = 0
        for co in COMPANIES:
            email = employer_email(co)
            user, _ = User.objects.get_or_create(email=email, defaults={
                "user_type": User.EMPLOYER, "is_active": True,
                "consented_to_terms": True, "consented_at": now,
            })
            user.user_type = User.EMPLOYER
            user.set_password(PASSWORD)
            user.save()
            _mark_email_verified(user, email)

            b_code, b_name = self._barangay(co["barangays"])
            main_address = f"{co['bldg']}, {co['street']}, Brgy. {b_name}, Iloilo City, Iloilo"
            company, _ = Company.objects.update_or_create(
                slug=co["slug"],
                defaults={
                    "name": co["name"], "type_of_company": co["type"],
                    "nature_of_company": co["nature"], "description": co["desc"],
                    "company_size": co["size"], "website": co["website"],
                    "company_email": email, "recruitment_email": email,
                    "main_branch_address": main_address,
                    "iloilo_bldg_unit": co["bldg"], "iloilo_street": co["street"],
                    "iloilo_barangay_code": b_code, "iloilo_barangay_name": b_name,
                    "iloilo_city": "Iloilo City", "iloilo_province": "Iloilo",
                    "verification_status": Company.VERIFIED, "verified_at": now,
                },
            )
            company.sector_badges.set([sectors[c] for c in co["sectors"]])

            first, last, position, sex = co["rep"]
            EmployerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "company": company, "first_name": first, "last_name": last,
                    "position": position, "sex": sex,
                    "birthday": date(today.year - rng.randint(30, 48), rng.randint(1, 12), rng.randint(1, 28)),
                    "phone": f"0917{rng.randint(1000000, 9999999)}", "email": email,
                },
            )

            # Jobs: rebuilt each run so re-seeding never duplicates them.
            company.job_postings.all().delete()
            for (title, edu, course, months, req, pref, certs, slots, (smin, smax), desc) in co["jobs"]:
                job = JobPosting.objects.create(
                    company=company, title=title, description=desc,
                    location_type=JobPosting.ILOILO,
                    bldg_unit=co["bldg"], street=co["street"],
                    barangay_code=b_code, barangay_name=b_name, city="Iloilo City",
                    slots=slots, salary_min=smin, salary_max=smax,
                    status=JobPosting.STATUS_OPEN, visibility=JobPosting.VISIBILITY_PUBLIC,
                    approval_status=JobPosting.APPROVAL_APPROVED,
                    submitted_at=now, reviewed_at=now,
                    contact_email=email, contact_phone=f"0917{rng.randint(1000000, 9999999)}",
                    search_keywords=", ".join([co["nature"], title] + req),
                )
                JobEducationRequirement.objects.create(job=job, level=edu, course_degree=course)
                JobExperienceRequirement.objects.create(
                    job=job, months_required=months, any_experience_accepted=True)
                for s in req:
                    JobSkillRequirement.objects.create(job=job, name=s, is_required=True)
                for s in pref:
                    JobSkillRequirement.objects.create(job=job, name=s, is_required=False)
                for cname, corg in certs:
                    JobCertificationRequirement.objects.create(
                        job=job, name=cname, issuing_org=corg, is_required=True)
                job_total += 1
        self.stdout.write(self.style.SUCCESS(f"Companies: {len(COMPANIES)}   Jobs: {job_total}"))

        # ── Jobseekers ─────────────────────────────────────────────
        for js in JOBSEEKERS:
            email = jobseeker_email(js)
            user, _ = User.objects.get_or_create(email=email, defaults={
                "user_type": User.JOBSEEKER, "is_active": True,
                "consented_to_terms": True, "consented_at": now,
            })
            user.user_type = User.JOBSEEKER
            user.set_password(PASSWORD)
            user.save()
            _mark_email_verified(user, email)

            b_code, b_name = self._barangay([js["barangay"]])
            profile, _ = JobseekerProfile.objects.update_or_create(
                user=user,
                defaults={
                    "first_name": js["first"], "middle_name": js["middle"], "last_name": js["last"],
                    "sex": js["sex"], "civil_status": js["civil"],
                    "date_of_birth": date(today.year - js["age"], rng.randint(1, 12), rng.randint(1, 28)),
                    "house_unit": js["house"], "street_barangay": js["street"],
                    "barangay": b_name, "barangay_code": b_code,
                    "city_municipality": "Iloilo City", "city_code": city_code,
                    "province": "Iloilo", "province_code": province_code,
                    "phone": f"0917{rng.randint(1000000, 9999999)}", "contact_email": email,
                    "profile_complete": True, "profile_visibility": "public",
                    "sector_badge_visibility": "public", "bio": js["bio"],
                },
            )
            profile.sectors.set([sectors[c] for c in js["sectors"]])

            # Rebuild resume sections so reruns stay clean.
            for rel in (profile.educations, profile.skills, profile.experiences, profile.certifications):
                rel.all().delete()

            level, course, school = js["edu"]
            end = today.year - max(js["age"] - 22, 1) if level == "bachelor" else today.year - max(js["age"] - 18, 1)
            Education.objects.create(profile=profile, level=level, course_degree=course,
                                     institution=school, year_started=end - 4 if level == "bachelor" else end - 2,
                                     year_ended=end)
            for s in js["skills"]:
                Skill.objects.create(profile=profile, name=s)
            for (pos, comp, yrs_ago, dur, desc) in js["exp"]:
                start = today.year - yrs_ago
                WorkExperience.objects.create(
                    profile=profile, position=pos, company=comp, description=desc,
                    month_started=MONTHS[rng.randint(0, 5)], year_started=start,
                    month_ended=MONTHS[rng.randint(6, 11)], year_ended=start + dur,
                )
            for (name, org, yrs_ago) in js["certs"]:
                Certification.objects.create(profile=profile, name=name, issuing_org=org,
                                             year_received=today.year - yrs_ago)
        self.stdout.write(self.style.SUCCESS(f"Jobseekers: {len(JOBSEEKERS)}"))

        # ── Credentials file ───────────────────────────────────────
        path = settings.BASE_DIR / "demo_credentials.txt"
        path.write_text(credentials_text(), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Credentials written to {path}"))
