# Restoration and fixes

- Replaced the class template README with setup, data definitions, architecture,
  testing, deployment, and team attribution.
- Split the monolithic backend into application factory, routes, DB layer, and CLI.
- Added complete schemas and explicit initialization/import commands; no old GCP
  database or unavailable synthetic seed is required.
- Added SQLite for an offline local demo; retained MySQL 8.4 and Cloud SQL support.
- Replaced the synthetic catalog dependency with reproducible official downloads
  and a committed, provenance-tracked normalized real-data snapshot.
- Removed hardcoded database secrets, cloud IP addresses, debug mode, and HTTP
  endpoints that execute schema DDL. Schema changes use the local administrative CLI.
- Replaced plaintext password comparison/storage with Werkzeug password hashing,
  signed cookie sessions, CSRF protection, and server-enforced account ownership.
- Restricted program mutations and major–job transactions to administrators.
- Scoped comparison deletion to its owning user.
- Added payload/ID/money validation and request-scoped connection cleanup/rollback.
- Repaired procedure creation: connector SQL contains no `DELIMITER` directives.
- Removed the recommendation fallback that silently ignored budget and major.
- Made missing job mappings preserve program detail results through LEFT JOINs.
- Fixed the transaction's string-versus-integer job ID lookup and same-job case.
- Added stable primary keys, foreign keys, indexes, idempotent imports, and duplicate
  bookmark handling without swallowing foreign-key failures.
- Made alerts use database-generated IDs instead of `MAX(id)+1`; suppressed
  earnings do not trigger a low-earnings alert.
- Fixed no-op updates being incorrectly reported as missing records.
- Escaped rendered API text (including saved notes), displayed missing money
  explicitly, added tuition/source details to comparison cards.
- Fixed admin-only DOM initialization crashing other pages, replaced timer-based
  initialization with awaited loads, removed dead auto-bookmark UI code, fixed
  alert navigation/page markup, and made logout invalidate the server session.
- Added SQLite/MySQL CI and tests for actual import and core workflows.

## Boundaries

This is a restored course/portfolio application. Public deployment still needs
operational configuration: HTTPS, secret management, database backups, login rate
limiting, monitoring, and an account provisioning/recovery policy. Account creation
currently uses the CLI; public registration and password recovery are not implemented.

No cloud deployment, old-database migration, or job-data enrichment was performed.
The original local archive and binary course reports are preserved outside this
clean repository. Historical course notes may describe abandoned functionality.

The old project contained live-looking database credentials. They are not present
in this repository. If that database/account still exists, rotate its credentials
before reusing it.
