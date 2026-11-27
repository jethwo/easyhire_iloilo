"""Populate the MySQL / MariaDB ``mysql.time_zone*`` tables.

Django runs with ``USE_TZ = True``, and the analytics views use
``TruncMonth``, which Django compiles to ``CONVERT_TZ(col, 'UTC',
'Asia/Manila')`` on MySQL. That function returns **NULL** unless the
server's time zone tables have been loaded, so the monthly charts come back
empty with no error to explain why.

The usual fix is ``mysql_tzinfo_to_sql /usr/share/zoneinfo``, which does not
work on Windows: there is no system zoneinfo tree, and the bundled
converter cannot walk one it is pointed at. This command does the same job
in Python, reading the TZif files from the ``tzdata`` package that Django
already requires on Windows — so it needs no download and no system files.

By default it loads only the zones the project actually converts between
(UTC and ``settings.TIME_ZONE``). Pass ``--all`` for the full database.

    python manage.py load_mysql_timezones
    python manage.py load_mysql_timezones --all

Caveat for ``--all``: the ``tzdata`` wheel ships "slim" TZif files, which
describe future DST transitions with a POSIX rule string rather than
explicit transitions. MySQL's tables cannot represent that rule, so for
zones that observe DST, conversions past the last explicit transition fall
back to the final offset. This does not affect the Philippines, which has
had no DST since 1978 and a fixed +08:00 offset.
"""
import struct
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

# Transitions older than this are dropped: they are the synthetic "big
# bang" sentinel that version-2 TZif files open with, and no date the
# application handles is anywhere near it.
_MIN_TRANSITION = -(2 ** 31)


def _parse_tzif(raw):
    """Return (transitions, type_indices, types) from a TZif file.

    `types` is a list of (utc_offset_seconds, is_dst, abbreviation).
    Version 2+ files carry a 32-bit block followed by a 64-bit one; the
    64-bit block is authoritative, so the first is skipped when present.
    """
    if raw[:4] != b"TZif":
        raise ValueError("not a TZif file")
    version = raw[4:5]

    def counts_at(offset):
        # isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt
        return struct.unpack_from(">6I", raw, offset)

    pos = 20
    isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt = counts_at(pos)
    pos += 24

    if version in (b"2", b"3", b"4"):
        # Skip the legacy 32-bit block, then re-read the 64-bit header.
        pos += (timecnt * 4 + timecnt + typecnt * 6
                + charcnt + leapcnt * 8 + isstdcnt + isutcnt)
        if raw[pos:pos + 4] != b"TZif":
            raise ValueError("second TZif header missing")
        pos += 20
        isutcnt, isstdcnt, leapcnt, timecnt, typecnt, charcnt = counts_at(pos)
        pos += 24
        time_fmt, time_size = ">q", 8
    else:
        time_fmt, time_size = ">i", 4

    transitions = [
        struct.unpack_from(time_fmt, raw, pos + i * time_size)[0]
        for i in range(timecnt)
    ]
    pos += timecnt * time_size

    indices = list(raw[pos:pos + timecnt])
    pos += timecnt

    raw_types = [struct.unpack_from(">ibB", raw, pos + i * 6) for i in range(typecnt)]
    pos += typecnt * 6

    abbrev_blob = raw[pos:pos + charcnt]
    types = []
    for utc_offset, is_dst, abbrev_index in raw_types:
        end = abbrev_blob.index(b"\0", abbrev_index)
        types.append((utc_offset, is_dst,
                      abbrev_blob[abbrev_index:end].decode("ascii")))

    return transitions, indices, types


def _zoneinfo_root():
    """Locate the tzdata package's zoneinfo tree."""
    try:
        import tzdata
    except ImportError as exc:  # pragma: no cover - tzdata is a Django dep on Windows
        raise CommandError(
            "The 'tzdata' package is not installed, so there is no zoneinfo "
            "tree to read. Install it with: pip install tzdata"
        ) from exc
    root = Path(tzdata.__file__).parent / "zoneinfo"
    if not root.is_dir():
        raise CommandError(f"zoneinfo directory not found under {root}")
    return root


class Command(BaseCommand):
    help = "Load time zone data into the MySQL/MariaDB mysql.time_zone* tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all", action="store_true", dest="load_all",
            help="Load every zone in tzdata instead of just UTC and "
                 "settings.TIME_ZONE.",
        )

    def handle(self, *args, **options):
        if connection.vendor != "mysql":
            raise CommandError(
                f"This command only applies to MySQL/MariaDB; the current "
                f"connection is '{connection.vendor}'. Set DB_ENGINE=mysql."
            )

        root = _zoneinfo_root()

        if options["load_all"]:
            names = sorted(
                str(p.relative_to(root)).replace("\\", "/")
                for p in root.rglob("*")
                if p.is_file() and p.suffix == "" and p.read_bytes()[:4] == b"TZif"
            )
        else:
            names = sorted({"UTC", settings.TIME_ZONE})

        self.stdout.write(f"Loading {len(names)} zone(s) from {root}")

        loaded = 0
        skipped = []
        with connection.cursor() as cursor:
            for name in names:
                path = root.joinpath(*name.split("/"))
                if not path.is_file():
                    skipped.append(f"{name} (no TZif file)")
                    continue
                try:
                    transitions, indices, types = _parse_tzif(path.read_bytes())
                except (ValueError, struct.error, IndexError) as exc:
                    skipped.append(f"{name} ({exc})")
                    continue
                if not types:
                    skipped.append(f"{name} (no transition types)")
                    continue

                self._load_zone(cursor, name, transitions, indices, types)
                loaded += 1

        for line in skipped:
            self.stdout.write(self.style.WARNING(f"  skipped {line}"))

        verified = self._verify(names)
        self.stdout.write(self.style.SUCCESS(
            f"Loaded {loaded} zone(s). CONVERT_TZ check: {verified}"
        ))

    def _load_zone(self, cursor, name, transitions, indices, types):
        """Replace this zone's rows, keeping its existing id when present."""
        cursor.execute(
            "SELECT `Time_zone_id` FROM mysql.time_zone_name WHERE `Name` = %s", [name]
        )
        row = cursor.fetchone()
        if row:
            zone_id = row[0]
            cursor.execute(
                "DELETE FROM mysql.time_zone_transition WHERE `Time_zone_id` = %s",
                [zone_id])
            cursor.execute(
                "DELETE FROM mysql.time_zone_transition_type WHERE `Time_zone_id` = %s",
                [zone_id])
        else:
            cursor.execute(
                "INSERT INTO mysql.time_zone (`Use_leap_seconds`) VALUES ('N')")
            cursor.execute("SELECT LAST_INSERT_ID()")
            zone_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO mysql.time_zone_name (`Name`, `Time_zone_id`) VALUES (%s, %s)",
                [name, zone_id])

        cursor.executemany(
            "INSERT INTO mysql.time_zone_transition_type "
            # `Offset` is a reserved word in MariaDB, so these are quoted.
            "(`Time_zone_id`, `Transition_type_id`, `Offset`, `Is_DST`, `Abbreviation`) "
            "VALUES (%s, %s, %s, %s, %s)",
            [(zone_id, i, offset, int(is_dst), abbrev)
             for i, (offset, is_dst, abbrev) in enumerate(types)],
        )

        rows = [
            (zone_id, when, type_index)
            for when, type_index in zip(transitions, indices)
            if when >= _MIN_TRANSITION
        ]
        if rows:
            cursor.executemany(
                "INSERT INTO mysql.time_zone_transition "
                "(`Time_zone_id`, `Transition_time`, `Transition_type_id`) "
                "VALUES (%s, %s, %s)",
                rows,
            )

    def _verify(self, names):
        """Prove CONVERT_TZ now resolves for every zone we just loaded."""
        failures = []
        with connection.cursor() as cursor:
            for name in names:
                cursor.execute(
                    "SELECT CONVERT_TZ('2026-06-15 04:00:00', 'UTC', %s)", [name]
                )
                if cursor.fetchone()[0] is None:
                    failures.append(name)
        if failures:
            return f"FAILED for {', '.join(failures)}"
        return f"all {len(names)} zone(s) resolve"
