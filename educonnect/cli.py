"""Explicit, repeatable initialization and data import commands."""

import csv
from pathlib import Path

import click
from flask import current_app
from werkzeug.security import generate_password_hash

from .db import execute, get_db, query

ROOT = Path(__file__).resolve().parent.parent


def init_database():
    db = get_db()
    backend = current_app.config["DATABASE_BACKEND"]
    schema = (ROOT / "sql" / f"schema.{backend}.sql").read_text(encoding="utf-8")
    if backend == "sqlite":
        db.raw.executescript(schema)
        db.raw.executescript((ROOT / "sql" / "trigger.sqlite.sql").read_text(encoding="utf-8"))
    else:
        cursor = db.cursor()
        try:
            for statement in schema.split(";"):
                if statement.strip():
                    cursor.execute(statement)
            cursor.execute("DROP TRIGGER IF EXISTS salary_alert_trigger")
            cursor.execute((ROOT / "sql" / "trigger.mysql.sql").read_text(encoding="utf-8"))
            cursor.execute("DROP PROCEDURE IF EXISTS RecommendProgramsForUser")
            # DELIMITER is a mysql shell directive, not SQL for the connector.
            cursor.execute((ROOT / "sql" / "recommend.mysql.sql").read_text(encoding="utf-8"))
        finally:
            cursor.close()
    db.commit()


def import_snapshot(directory):
    """Upsert catalog data in one transaction; preserve IDs and user records.

    No deletes: an updated snapshot cannot silently cascade into bookmarks.
    Only source-managed programs are refreshed; manually edited rows are kept.
    """
    db = get_db()
    backend = current_app.config["DATABASE_BACKEND"]
    counts = {}
    cursor = db.cursor()
    try:
        for table, filename, key in [
            ("University", "universities.csv", "UniversityID"),
            ("Major", "majors.csv", "MajorID"),
            ("Program", "programs.csv", "SourceKey"),
        ]:
            with (Path(directory) / filename).open(encoding="utf-8", newline="") as file:
                reader = csv.DictReader(file)
                columns = reader.fieldnames
                # The input schema is fixed, never interpolate untrusted column names.
                expected = {
                    "University": [
                        "UniversityID",
                        "Name",
                        "Location",
                        "City",
                        "Tuition",
                        "TuitionOutState",
                        "Website",
                        "Source",
                    ],
                    "Major": ["MajorID", "MajorName", "Field", "CIPCode"],
                    "Program": [
                        "Name",
                        "UniversityID",
                        "MajorID",
                        "DegreeType",
                        "MedianSalary",
                        "Source",
                        "SourceKey",
                        "EarningsMetric",
                    ],
                }[table]
                if columns != expected:
                    raise ValueError(f"Unexpected columns in {filename}")
                updates = [column for column in columns if column != key]
                sql = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join(['%s'] * len(columns))})"
                if backend == "sqlite":
                    sql += f" ON CONFLICT({key}) DO UPDATE SET " + ",".join(
                        f"{c}=excluded.{c}" for c in updates
                    )
                    if table == "Program":
                        sql += " WHERE Program.Source LIKE 'College Scorecard%'"
                else:
                    sql += " ON DUPLICATE KEY UPDATE "
                    if table == "Program":
                        # Source assignment last: each condition checks the existing provenance.
                        updates = [c for c in updates if c != "Source"] + ["Source"]
                        sql += ",".join(
                            f"{c}=IF(Source LIKE 'College Scorecard%',VALUES({c}),{c})"
                            for c in updates
                        )
                    else:
                        sql += ",".join(f"{c}=VALUES({c})" for c in updates)
                counts[table] = 0
                batch = []
                for row in reader:
                    batch.append(
                        tuple(row[column] if row[column] != "" else None for column in columns)
                    )
                    counts[table] += 1
                    if len(batch) == 500:
                        cursor.executemany(sql, batch)
                        batch = []
                if batch:
                    cursor.executemany(sql, batch)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cursor.close()
    return counts


def register(app):
    @app.cli.command("init-db")
    def init_db_command():
        """Create missing tables, indexes, trigger and MySQL recommendation procedure."""
        init_database()
        click.echo("Database initialized (existing rows preserved).")

    @app.cli.command("import-scorecard")
    @click.option(
        "--directory", default=str(ROOT / "data" / "processed"), type=click.Path(exists=True)
    )
    def import_command(directory):
        """Import the verified, normalized real-data snapshot."""
        click.echo(import_snapshot(directory))

    @app.cli.command("create-user")
    @click.option("--username", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @click.option("--admin", is_flag=True, help="Grant catalog administration privileges.")
    def create_user(username, password, admin):
        """Create a local account. No default passwords or sample personal records."""
        if not username.strip() or len(username) > 100 or not 12 <= len(password) <= 1024:
            raise click.ClickException("Username: 1–100 characters; password: 12–1024 characters.")
        if query("SELECT UserID FROM User WHERE Username=%s", (username.strip(),), one=True):
            raise click.ClickException("Username already exists")
        execute(
            "INSERT INTO User (Username,PasswordHash,IsAdmin) VALUES (%s,%s,%s)",
            (username.strip(), generate_password_hash(password), int(admin)),
        )
        get_db().commit()
        click.echo("Account created. Log in, then select a preferred major under User Info.")
