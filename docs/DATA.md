# Data provenance

Publisher: U.S. Department of Education, Office of Planning, Evaluation and Policy
Development, College Scorecard. The [official Data.gov catalog](https://catalog.data.gov/dataset/college-scorecard)
lists public access and a CC BY license link. Retain publisher/source attribution
when redistributing the transformed snapshot. These CSVs are a filtered,
normalized derivative, not an unmodified copy of the entire source.

## Pinned downloads

- [Institution-level release, 2025-05-19](https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_05192025.zip)
- [Field-of-study release, 2025-04-17](https://data.ed.gov/dataset/9dc70e6b-8426-4d71-b9d5-70ce6094a3f4/resource/ff68afc4-6d23-459d-9f60-4006e4f85583/download/most-recent-cohorts-field-of-study_04172025.zip)
- [Institution documentation](https://collegescorecard.ed.gov/assets/InstitutionDataDocumentation.pdf)
- [Field-of-study documentation](https://collegescorecard.ed.gov/assets/FieldOfStudyDataDocumentation.pdf)
- [Official API documentation](https://collegescorecard.ed.gov/data/api-documentation/)

The downloadable files were actually retrieved and parsed during restoration on
2026-10-12. `data/processed/manifest.json` records the precise download URLs,
archive hashes, output hashes, coverage counts, exclusions, metric definitions,
and normalization timestamp. The source releases are pinned for reproducibility;
this repository does not claim they are the newest releases available.

## Transformation

1. Read the single CSV in each ZIP directly; do not extract arbitrary archive paths.
2. Index institution rows by numeric `UNITID`.
3. Retain `CREDLEV=3` (bachelor's) field-of-study rows with a matching institution.
4. Retain the four-character CIP string, including leading zeros. `MajorID` is its
   integer representation; `CIPCode` preserves the official representation.
5. Define `SourceKey` as `UNITID:CIPCODE:3`. Reject conflicting duplicates rather
   than silently selecting one. Program IDs are assigned by the database.
6. Use only `EARN_MDN_HI_2YR` for earnings. No fallback to another year, campus-wide
   earnings, occupational pay, or estimated values.
7. Convert `NULL`, empty, and `PrivacySuppressed` measurements to SQL `NULL` through
   empty CSV cells. Preserve a reported zero as zero.
8. Store annual undergraduate `TUITIONFEE_IN` and `TUITIONFEE_OUT` separately.

The snapshot has 66,342 program records at 2,378 institutions and 371 CIP categories.
27,456 records contain earnings. 37,878 are privacy-suppressed and 1,008 contain
source `NULL`. The transformation excludes 151,685 non-bachelor's rows and 5,483
bachelor's rows without a match in the institution archive. Exclusions mean this
is not a comprehensive inventory of every US school or degree program.

Programs are field-of-study/credential categories, not exact course listings.
Source earnings can be pooled across institutional reporting units and cohorts;
do not imply campus-specific precision beyond the source's definitions. The
institution and program releases have different cohort schedules. A download
release date is not an observation year. No cross-source salaries or tuition
amounts are synthesized to bridge these differences.

## Import behavior

`flask --app main import-scorecard` upserts universities and majors by their source
IDs and programs by `SourceKey`, inside one transaction. It preserves user IDs,
bookmarks, notes, and program IDs. User-edited/supplied programs are marked with
their own provenance and excluded from automatic source updates. A failed import
rolls back all catalog writes.

Refreshes update the source-managed rows in the input. They do not delete rows
absent from a newer snapshot or migrate historical synthetic records. Use a fresh
database for this version; a new release requires a reviewed retention/migration
decision if full replacement of an existing catalog is desired. When importing a
different prepared directory, its provenance should be recorded separately; the
UI source manifest describes the bundled snapshot.

## API alternative and jobs

College Scorecard has an official API with an API key signup through its data
site. For this project, the bulk downloads avoid an API key requirement, quota,
network latency on searches, and mutable results. No API key is bundled and no
third-party proxy is used.

College Scorecard does not provide company job records, job postings, or a
validated CIP-to-job mapping. We intentionally leave `Job` and `MajorJob` empty;
the existing transaction remains available for separately sourced data. Do not
label synthetic job fixtures from automated tests as real observations.
