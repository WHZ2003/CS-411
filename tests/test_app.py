from werkzeug.security import check_password_hash

from conftest import login
from educonnect.db import execute, get_db, query


def test_pages_and_search(client):
    for url in ["/", "/login", "/admin", "/alert", "/userinfo"]:
        response = client.get(url)
        assert response.status_code == 200
        assert b"csrf-token" in response.data
    response = client.get("/api/programs/search?major=Computer&location=IL&min_salary=60000")
    assert [p["ProgramID"] for p in response.json] == [1]
    assert client.get("/api/programs/3").json["MedianSalary"] is None
    assert len(client.get("/api/programs?limit=1").json) == 1
    assert client.get("/api/programs/keyword-search?q=%27%20OR%201%3D1--").json == []
    assert client.get("/api/programs/keyword-search").status_code == 400
    assert client.get("/api/programs/search?min_salary=not-a-number").status_code == 400
    assert client.get("/api/programs/99999").status_code == 404
    assert client.get("/api/programs/1/details").json[0]["JobID"] is None


def test_authentication_and_csrf(client, app):
    assert client.get("/api/users/1/info").status_code == 401
    assert client.post("/api/login", json={}).status_code == 403
    token = client.get("/api/session").json["csrf_token"]
    assert (
        client.post(
            "/api/login",
            json={"username": "alice", "password": "wrong-password"},
            headers={"X-CSRF-Token": token},
        ).status_code
        == 401
    )
    headers = login(client)
    assert client.get("/api/users/1/info").json["Username"] == "alice"
    assert client.get("/api/users/2/info").status_code == 403
    assert (
        client.post(
            "/api/bookmarks", json={"user_id": 2, "program_id": 1}, headers=headers
        ).status_code
        == 403
    )
    assert client.post("/api/programs", json={}, headers=headers).status_code == 403
    assert client.get("/api/admin/major-jobs/1107").status_code == 403
    assert client.post("/api/logout", headers=headers).status_code == 200
    assert client.get("/api/users/1/info").status_code == 401


def test_bookmarks_trigger_and_clear(client, headers):
    for _ in range(2):
        assert (
            client.post("/api/bookmarks", json={"program_id": 2}, headers=headers).status_code
            == 201
        )
    assert len(client.get("/api/users/1/bookmarks").json) == 1
    alerts = client.get("/api/users/1/alerts").json
    assert len(alerts) == 1
    # Unknown earnings must not produce a low-earnings alert.
    assert client.post("/api/bookmarks", json={"program_id": 3}, headers=headers).status_code == 201
    assert len(client.get("/api/users/1/alerts").json) == 1
    assert (
        client.post("/api/bookmarks", json={"program_id": 99999}, headers=headers).status_code
        == 404
    )
    assert (
        client.delete(f"/api/users/1/alerts/{alerts[0]['AlertID']}", headers=headers).status_code
        == 200
    )
    assert client.delete("/api/users/1/bookmarks", headers=headers).json["deleted"] == 2


def test_recommendation_never_relaxes_constraints(client, headers):
    rows = client.get("/api/users/1/recommend?max_tuition=25000&min_salary=60000").json
    assert [p["ProgramID"] for p in rows] == [1]
    assert float(rows[0]["AvgTuitionForMajor"]) == 20000
    assert client.get("/api/users/1/recommend?max_tuition=100&min_salary=60000").json == []
    assert client.get("/api/users/1/recommend?min_salary=NaN").status_code == 400
    assert (
        client.put(
            "/api/users/1/preferences",
            json={"preferred_major": None, "preferred_job": None},
            headers=headers,
        ).status_code
        == 200
    )
    assert client.get("/api/users/1/recommend").json == []


def test_preferences_and_password(client, headers, app):
    assert (
        client.put(
            "/api/users/1/preferences",
            json={"preferred_major": "1107", "preferred_job": ""},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/users/1/preferences", json={"preferred_major": 9999}, headers=headers
        ).status_code
        == 409
    )
    assert client.get("/api/users/1/info").json["PreferredMajorID"] == 1107
    assert (
        client.put(
            "/api/users/1/password", json={"new_password": "short"}, headers=headers
        ).status_code
        == 400
    )
    assert (
        client.put(
            "/api/users/1/password", json={"new_password": "changed-password-123"}, headers=headers
        ).status_code
        == 200
    )
    with app.app_context():
        hashed = query("SELECT PasswordHash FROM User WHERE UserID=1", one=True)["PasswordHash"]
        assert hashed != "changed-password-123"
        assert check_password_hash(hashed, "changed-password-123")


def test_comparison_ownership(client, headers, app):
    payload = {"program1_id": 1, "program2_id": 2, "note": "<img src=x onerror=alert(1)>"}
    assert client.post("/api/comparisons", json=payload, headers=headers).status_code == 201
    row = client.get("/api/comparisons/1").json[0]
    assert row["NoteFromUser"] == payload["note"]  # Escaping is performed by the renderer.
    bob = app.test_client()
    bob_headers = login(bob, "bob")
    assert (
        bob.delete(f"/api/comparisons/{row['ComparisonID']}", headers=bob_headers).status_code
        == 404
    )
    assert len(client.get("/api/comparisons/1").json) == 1
    assert (
        client.delete(f"/api/comparisons/{row['ComparisonID']}", headers=headers).status_code == 200
    )
    assert (
        client.post(
            "/api/comparisons", json={"program1_id": 1, "program2_id": 1}, headers=headers
        ).status_code
        == 400
    )


def test_admin_crud_and_noop_update(client):
    headers = login(client, "admin")
    payload = {
        "name": "Manual program",
        "university_id": 1,
        "major_id": 1107,
        "degree_type": "Bachelors Degree",
        "median_salary": None,
    }
    created = client.post("/api/programs", json=payload, headers=headers)
    assert created.status_code == 201
    pid = created.json["ProgramID"]
    assert created.json["Source"] == "User supplied"
    for _ in range(2):
        assert client.put(f"/api/programs/{pid}", json=payload, headers=headers).status_code == 200
    assert (
        client.put(f"/api/programs/{pid}", json={"median_salary": -1}, headers=headers).status_code
        == 400
    )
    assert client.delete(f"/api/programs/{pid}", headers=headers).status_code == 200
    assert client.get(f"/api/programs/{pid}").status_code == 404


def test_transaction_handles_string_ids_and_rolls_back(client, app):
    headers = login(client, "admin")
    with app.app_context():
        for jid, title, salary in [
            (1, "Low", 20000),
            (2, "Replacement", 60000),
            (3, "High", 100000),
        ]:
            execute(
                "INSERT INTO Job (JobID,JobTitle,AvgSalary) VALUES (%s,%s,%s)", (jid, title, salary)
            )
        execute("INSERT INTO MajorJob (MajorID,JobID) VALUES (1107,1)")
        execute("INSERT INTO MajorJob (MajorID,JobID) VALUES (1107,3)")
        get_db().commit()
    payload = {"major_id": "1107", "job1": "1", "job2": "999", "threshold": 1000}
    assert (
        client.post("/api/admin/update-major-jobs", json=payload, headers=headers).status_code
        == 400
    )
    with app.app_context():
        assert query("SELECT JobID FROM MajorJob WHERE MajorID=1107 AND JobID=1", one=True)
    payload["job2"] = "2"
    response = client.post("/api/admin/update-major-jobs", json=payload, headers=headers)
    assert response.status_code == 200
    assert response.json["switched"] is True
    with app.app_context():
        assert not query("SELECT JobID FROM MajorJob WHERE MajorID=1107 AND JobID=1", one=True)
        assert query("SELECT JobID FROM MajorJob WHERE MajorID=1107 AND JobID=2", one=True)


def test_invalid_json(client, headers):
    assert client.post("/api/bookmarks", json=[1, 2], headers=headers).status_code == 400
    assert (
        client.post("/api/bookmarks", json={"program_id": True}, headers=headers).status_code == 400
    )
