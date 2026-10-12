import os
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from educonnect import create_app
from educonnect.cli import init_database
from educonnect.db import execute, get_db


@pytest.fixture
def app(tmp_path):
    backend = os.getenv("TEST_DATABASE_BACKEND", "sqlite")
    config = {
        "TESTING": True,
        "SECRET_KEY": "test-only-key",
        "DATABASE_BACKEND": backend,
        "DATABASE_PATH": str(tmp_path / "test.sqlite3"),
        "SESSION_COOKIE_SECURE": False,
    }
    if backend == "mysql":
        # Only connect to an explicitly designated test database.
        config["DB_NAME"] = os.environ["TEST_DB_NAME"]
        if not config["DB_NAME"].endswith("_test"):
            raise ValueError("TEST_DB_NAME must end in _test")
    app = create_app(config)
    with app.app_context():
        init_database()
        if backend == "mysql":
            for table in [
                "Alert",
                "Comparison",
                "Bookmark",
                "User",
                "MajorJob",
                "Job",
                "Program",
                "Major",
                "University",
            ]:
                execute(f"DELETE FROM {table}")
        execute("""INSERT INTO University (UniversityID,Name,Location,City,Tuition,TuitionOutState,Website,Source)
            VALUES (1,'Test University','IL','Test City',20000,40000,'example.invalid','Test fixture')""")
        execute(
            "INSERT INTO Major (MajorID,MajorName,Field,CIPCode) VALUES (1107,'Computer Science.','CIP 11','1107')"
        )
        execute(
            "INSERT INTO Major (MajorID,MajorName,Field,CIPCode) VALUES (5201,'Business','CIP 52','5201')"
        )
        for pid, major, earnings in [
            (1, 1107, 80000),
            (2, 1107, 40000),
            (3, 1107, None),
            (4, 5201, 100000),
        ]:
            execute(
                """INSERT INTO Program (ProgramID,Name,UniversityID,MajorID,DegreeType,MedianSalary,Source,SourceKey,EarningsMetric)
                VALUES (%s,%s,1,%s,'Bachelors Degree',%s,'Test fixture',%s,'EARN_MDN_HI_2YR')""",
                (pid, f"Test Program {pid}", major, earnings, f"test:{pid}"),
            )
        for uid, name, admin in [(1, "alice", 0), (2, "bob", 0), (3, "admin", 1)]:
            execute(
                "INSERT INTO User (UserID,Username,PasswordHash,PreferredMajor,IsAdmin) VALUES (%s,%s,%s,1107,%s)",
                (uid, name, generate_password_hash("test-password-123"), admin),
            )
        get_db().commit()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username="alice"):
    token = client.get("/api/session").json["csrf_token"]
    response = client.post(
        "/api/login",
        json={"username": username, "password": "test-password-123"},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json["csrf_token"]}


@pytest.fixture
def headers(client):
    return login(client)


@pytest.fixture
def snapshot_dir():
    return Path(__file__).resolve().parents[1] / "data" / "processed"
