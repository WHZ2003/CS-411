# MySQL / GCP deployment notes

Local SQLite is the quickest demonstration path. The production path retains the
original Flask + Gunicorn + MySQL architecture. This restoration does not deploy
cloud resources or connect to the old database.

1. Provision a new MySQL 8.4 database/schema and database user. The initialization
   identity needs table, index, trigger, and routine privileges. A runtime identity
   should have only needed data privileges plus EXECUTE on the recommendation
   procedure. Follow Cloud SQL's connection and IAM setup for your project.
2. Configure `.env` for an authorized local connection (for example through Cloud
   SQL Auth Proxy), run `init-db`, `import-scorecard`, and `create-user --admin`.
   Do not run these against the old schema without a separately reviewed migration.
3. Copy `deploy/app.yaml.example` to root `app.yaml`, fill in the Cloud SQL
   instance connection name and non-secret settings. The root file is gitignored.
4. Provide `SECRET_KEY` and `DB_PASSWORD` through your deployment's protected
   configuration/secret-management workflow. Do not commit them. Set
   `SESSION_COOKIE_SECURE=true` for HTTPS. The app refuses to start on App Engine
   without `SECRET_KEY`.
5. Use Python 3.12 and the WSGI command in the example. Deploy only after verifying
   account access, HTTPS, database connectivity, least-privilege permissions,
   backups, and operational controls for the intended audience.

`DB_UNIX_SOCKET=/cloudsql/PROJECT:REGION:INSTANCE` selects a Cloud SQL Unix socket
when available. On Windows/local machines use TCP host/port instead. Gunicorn is
installed only on non-Windows platforms; local Windows development uses Flask.

The database and sessions must not use App Engine's ephemeral local filesystem.
Set `DATABASE_BACKEND=mysql` in cloud deployment. Credentials, virtual environments,
local databases, raw archives, and tests are excluded by `.gcloudignore`.

The checked-in example is a template, not a tested deployment in a specific GCP
project. Cloud infrastructure, billing, TLS termination, secrets, login throttling,
and monitoring remain deployment responsibilities.
