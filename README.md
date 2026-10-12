# EduConnect — College & Program Explorer

UIUC **CS 411, Fall 2025 · Team 050 Hajimi**. A relational database project helping
students compare universities and undergraduate programs by location, tuition,
and graduate earnings, then build a personal shortlist.

The restored application runs locally without GCP, while retaining a **MySQL / GCP
Cloud SQL** deployment path and the course project's joins, transactions, stored
procedure, and bookmark alert trigger.

**Real data included:** 2,378 institutions, 371 CIP major categories, and **66,342
bachelor's program records** from the U.S. Department of Education's
[College Scorecard](https://catalog.data.gov/dataset/college-scorecard). The
normalized snapshot is committed, so the first run needs no API key or data download.
The data uses pinned 2025 releases, not a claim of current-year coverage.

## Features

- Search across program, major, institution, and state; filter earnings and tuition.
- Compare programs with annual in-state/out-of-state tuition and source provenance.
- Save private bookmarks, comparisons, notes, and preferred majors.
- Recommend programs satisfying the chosen major, tuition ceiling, and earnings floor.
- Trigger an alert when bookmarking a program with reported earnings below $60,000.
- Admin-only program CRUD; retained transactional major–job maintenance.
- Session authentication, password hashing, CSRF protection, and ownership checks.

## Run locally

Requires **Python 3.12+**. SQLite is the default; MySQL setup is below.

```powershell
git clone https://github.com/WHZ2003/CS-411.git
cd CS-411
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m flask --app main init-db
python -m flask --app main import-scorecard
python -m flask --app main create-user --username yourname
python main.py
```

On macOS/Linux, activate with `source .venv/bin/activate` instead. If PowerShell
blocks activation, use `.\.venv\Scripts\python.exe` in place of `python`.

Open **http://127.0.0.1:5001/login**. `create-user` prompts for a password of at
least 12 characters; no shared or hardcoded credentials are shipped. Add `--admin`
when creating an administrator. After login, select **User Info → Edit Preferences**
and choose a major before trying recommendations.

Try a keyword search for `Illinois Urbana` or a major search for `Computer Science`
with state `IL`. Search displays up to 200 rows; refine the query to narrow results.

## Data meaning and limitations

| Application field | Source | Meaning |
| --- | --- | --- |
| Institution | `UNITID`, `INSTNM`, `STABBR` | Official institution identifier, name, and state |
| Major | `CIPCODE`, `CIPDESC` | Four-digit field-of-study category; not a university's exact degree title |
| Program | `UNITID` + `CIPCODE` + `CREDLEV` | Institution/field/credential combination; bachelor's only (`CREDLEV=3`) |
| Tuition | `TUITIONFEE_IN` | Annual institution-level undergraduate in-state tuition and fees |
| Out-of-state tuition | `TUITIONFEE_OUT` | Retained separately and shown in comparisons |
| Median earnings | `EARN_MDN_HI_2YR` | Median earnings two years after completion for the source's covered population |

Earnings describe federally aided, working, non-enrolled graduates covered by the
source, not all graduates, job offers, or guaranteed salaries. **27,456** program
records report earnings; **38,886** have suppressed or unavailable earnings, which
remain SQL `NULL` and display as **Not reported**. Filters that require earnings
exclude those rows. Tuition is neither net price nor total degree cost.

`MedianSalary` remains the internal column/API name for compatibility with the
course project, but the UI labels the measure as earnings. The average-by-major
endpoint is an **unweighted average of reported program medians**, not the median
earnings of all students in that major.

The school and field-of-study releases pool different measurement years. Their
release dates do not imply that every metric measures 2025. See
[data provenance and reproducibility](docs/DATA.md) for URLs, hashes, exclusions,
coverage, and the optional official API.

College Scorecard does **not** contain company job postings or a validated
major-to-job mapping. `Job` and `MajorJob` are retained but empty. The related
course transaction is tested using isolated fixtures and requires a separately
sourced job dataset before use. User accounts and interactions are created by
users; they are not imported student records.

## Refresh or reproduce the snapshot

```powershell
python scripts/prepare_scorecard.py --download
python -m flask --app main import-scorecard
```

This redownloads the **same pinned releases**, normalizes them, and records archive
and output SHA-256 hashes. Without `--download`, cached archives under `data/raw/`
are reused. To adopt a newer release, deliberately update the source URLs and
metric mapping, then rerun tests; upstream schemas and cohort meanings may change.

The import is transactional and repeatable. Program IDs remain stable across
reimports, preserving bookmarks. User-edited programs are not overwritten, and
records absent from a later input are not automatically deleted. See `docs/DATA.md`
for the refresh boundary.

## MySQL and GCP

Create an **empty MySQL 8.4 database** and a database user with permission to create
tables, indexes, triggers, and procedures. Copy `.env.example` to `.env`, set
`DATABASE_BACKEND=mysql`, and configure `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`, and `DB_NAME`. Then run the same `init-db`, `import-scorecard`, and
`create-user` commands.

MySQL uses `sql/recommend.mysql.sql` and `sql/trigger.mysql.sql`; SQLite provides
equivalent local behavior. The old database is not contacted or modified.
`init-db` creates missing objects; it is **not a migration for an existing legacy
schema**. Back up any old database and use a fresh schema for this restoration.

See [deployment notes](docs/DEPLOYMENT.md) and `deploy/app.yaml.example` for App Engine
and Cloud SQL configuration. No cloud deployment or paid resources are created
by this repository. Original embedded database credentials have been removed.

## Tests

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
ruff check .
ruff format --check .
node --check static/app.js
```

GitHub Actions tests SQLite and MySQL 8.4, including real-snapshot imports,
idempotency, rollback, privacy-suppressed values, strict recommendations, ownership,
CSRF, password hashing, admin CRUD, the alert trigger, and the major–job transaction.
Node.js is only needed for the JavaScript syntax check, not for serving the app.

## Repository layout

```text
educonnect/         App factory, routes, database layer, CLI commands
main.py             Flask / WSGI entry point
templates/          Original project pages, corrected and annotated
static/             Frontend JavaScript and styles
sql/                SQLite and MySQL schema, triggers, recommendation procedure
scripts/            Reproducible official-data download and normalization
data/processed/     Real normalized snapshot and provenance manifest
tests/              Isolated API, transaction, importer, and data tests
docs/               Architecture, data, deployment, and course history
deploy/             Credential-free GCP configuration example
```

## Credits and restoration

Original authors: **Wenhao Zhang, Yuhui Liu, Tianxiang Wu, and Zixuan Huang**.
Original course metadata and revision notes are under `docs/course/`; these are
historical descriptions, not claims about current data coverage or deployment.
The original local project archive and binary course submissions were preserved
in their original location and were not rewritten. No code license was inferred
for the team's work. Dataset attribution is documented separately.

See [restoration changes](docs/CHANGES.md) for fixes and remaining boundaries.

中文：这是 UIUC CS411 的选校与专业比较项目。当前版本已用美国教育部真实数据替换
运行所需的合成高校/专业数据，提供不依赖 GCP 的本地启动方式，并保留 MySQL 课程功能。
收入缺失值不填造，职位数据尚未接入，推荐结果严格满足筛选条件。
