"""Download and normalize official College Scorecard archives (stdlib only).

Run from the repo root: python scripts/prepare_scorecard.py --download
Without --download, reuse data/raw/{institution,field-of-study}.zip.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    "institution": "https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_05192025.zip",
    "field-of-study": "https://data.ed.gov/dataset/9dc70e6b-8426-4d71-b9d5-70ce6094a3f4/resource/ff68afc4-6d23-459d-9f60-4006e4f85583/download/most-recent-cohorts-field-of-study_04172025.zip",
}
INSTITUTION_SOURCE = "College Scorecard institution release 2025-05-19"
PROGRAM_SOURCE = "College Scorecard field-of-study release 2025-04-17"
METRIC = "EARN_MDN_HI_2YR"


def number(value):
    """Preserve missing/suppressed values as NULL; never impute zero."""
    if value in (None, "", "NULL", "PrivacySuppressed", "NA"):
        return None
    try:
        result = Decimal(value)
    except InvalidOperation:
        raise ValueError(f"Invalid numeric source value: {value!r}") from None
    if not result.is_finite() or result < 0:
        raise ValueError(f"Invalid numeric source value: {value!r}")
    return str(result)


def archive_rows(path, required):
    with zipfile.ZipFile(path) as archive:
        members = [
            n
            for n in archive.namelist()
            if n.lower().endswith(".csv") and not n.startswith("__MACOSX/")
        ]
        if len(members) != 1:
            raise ValueError(f"Expected one CSV in {path}")
        with archive.open(members[0]) as file:
            reader = csv.DictReader(io.TextIOWrapper(file, encoding="utf-8-sig", newline=""))
            if not set(required).issubset(reader.fieldnames or []):
                raise ValueError(f"Missing required fields in {path}: {required}")
            yield from reader


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def prepare(raw, output):
    institutions = {}
    for row in archive_rows(
        raw / "institution.zip",
        ["UNITID", "INSTNM", "STABBR", "TUITIONFEE_IN", "TUITIONFEE_OUT", "CITY", "INSTURL"],
    ):
        unitid = row["UNITID"]
        if not unitid.isdigit():
            continue
        if unitid in institutions:
            raise ValueError(f"Duplicate institution {unitid}")
        institutions[unitid] = dict(
            UniversityID=int(unitid),
            Name=row["INSTNM"],
            Location=row["STABBR"],
            City=row["CITY"],
            Tuition=number(row["TUITIONFEE_IN"]),
            TuitionOutState=number(row["TUITIONFEE_OUT"]),
            Website=row["INSTURL"],
            Source=INSTITUTION_SOURCE,
        )
    majors, programs, used, excluded = {}, {}, set(), Counter()
    earnings_status = Counter()
    for row in archive_rows(
        raw / "field-of-study.zip", ["UNITID", "CIPCODE", "CIPDESC", "CREDLEV", "CREDDESC", METRIC]
    ):
        # Tuition is institution-level undergraduate tuition: only import bachelor's awards.
        if row["CREDLEV"] != "3":
            excluded["not_bachelors"] += 1
            continue
        unitid = row["UNITID"]
        if unitid not in institutions:
            excluded["unmatched_or_non_numeric_unitid"] += 1
            continue
        cip = row["CIPCODE"].zfill(4)
        if not re.fullmatch(r"\d{4}", cip):
            raise ValueError(f"Invalid CIP code: {cip}")
        key = f"{unitid}:{cip}:3"
        major = dict(
            MajorID=int(cip), MajorName=row["CIPDESC"], Field=f"CIP {cip[:2]}", CIPCode=cip
        )
        if cip in majors and major != majors[cip]:
            raise ValueError(f"Inconsistent CIP description: {cip}")
        majors[cip] = major
        program = dict(
            Name=row["CIPDESC"],
            UniversityID=int(unitid),
            MajorID=int(cip),
            DegreeType=row["CREDDESC"],
            MedianSalary=number(row[METRIC]),
            Source=PROGRAM_SOURCE,
            SourceKey=key,
            EarningsMetric=METRIC,
        )
        if key in programs:
            if program != programs[key]:
                raise ValueError(f"Conflicting duplicate program: {key}")
            excluded["identical_duplicate"] += 1
            continue
        programs[key] = program
        used.add(unitid)
        earnings_status[
            "reported" if program["MedianSalary"] is not None else row[METRIC] or "empty"
        ] += 1
    if not programs:
        raise ValueError("Source archives yielded no matched bachelor's programs")
    output.mkdir(parents=True, exist_ok=True)
    universities = [institutions[key] for key in sorted(used, key=int)]
    major_rows = [majors[key] for key in sorted(majors)]
    program_rows = [
        programs[key] for key in sorted(programs, key=lambda k: tuple(map(int, k.split(":"))))
    ]
    for filename, rows in [
        ("universities.csv", universities),
        ("majors.csv", major_rows),
        ("programs.csv", program_rows),
    ]:
        write_csv(output / filename, list(rows[0]), rows)
    manifest = {
        "publisher": "U.S. Department of Education, College Scorecard",
        "catalog_url": "https://catalog.data.gov/dataset/college-scorecard",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "US bachelor's programs (CREDLEV=3) joined to institutions by UNITID; not a complete current program catalog",
        "earnings_metric": METRIC,
        "earnings_definition": "Median earnings two years after completion for the federally aided working, non-enrolled population covered by the source; not job salary or all graduates",
        "tuition_definition": "TUITIONFEE_IN: annual institution-level undergraduate in-state tuition and fees; TUITIONFEE_OUT retained separately; not program-specific total cost or net price",
        "cohort_warning": "Pinned most-recent-cohort releases pool different observation years. Release date is not the year of all measurements. Consult the source documentation.",
        "sources": {
            name: {
                "url": url,
                "sha256": hashlib.sha256((raw / f"{name}.zip").read_bytes()).hexdigest(),
            }
            for name, url in SOURCES.items()
        },
        "counts": {
            "universities": len(universities),
            "majors": len(major_rows),
            "programs": len(program_rows),
        },
        "earnings_status": dict(earnings_status),
        "excluded_rows": dict(excluded),
        "normalized_sha256": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in ("universities.csv", "majors.csv", "programs.csv")
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "processed")
    args = parser.parse_args()
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    if args.download:
        for name, url in SOURCES.items():
            path = args.raw_dir / f"{name}.zip"
            temporary = path.with_suffix(".part")
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open("wb") as file:
                while chunk := response.read(1024 * 1024):
                    file.write(chunk)
            if not zipfile.is_zipfile(temporary):
                raise ValueError(f"Download is not a ZIP: {url}")
            temporary.replace(path)
    manifest = prepare(args.raw_dir, args.output_dir)
    print(json.dumps(manifest["counts"], indent=2))


if __name__ == "__main__":
    main()
