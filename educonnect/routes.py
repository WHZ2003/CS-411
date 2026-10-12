"""Original project API, with validated writes and session ownership checks."""

import json
import math
from pathlib import Path

from flask import abort, jsonify, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .db import execute, get_db, query

PROGRAM_SELECT = """
    SELECT p.ProgramID, p.Name AS ProgramName, p.DegreeType, p.MedianSalary,
           p.UniversityID, u.Name AS UniversityName, u.Location, u.Tuition,
           p.MajorID, m.MajorName, p.Source, p.SourceKey, p.EarningsMetric,
           u.TuitionOutState, u.Website, m.CIPCode
    FROM Program p JOIN University u ON p.UniversityID = u.UniversityID
    JOIN Major m ON p.MajorID = m.MajorID
"""


def body():
    return request.get_json(silent=True) or {}


def integer(value, name, *, optional=False):
    if optional and value in (None, ""):
        return None
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        result = int(str(value))
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a positive integer") from None
    if result < 1:
        raise ValueError(f"{name} must be a positive integer")
    return result


def amount(value, name, *, optional=False):
    if optional and value in (None, ""):
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a nonnegative number") from None
    if isinstance(value, bool) or not math.isfinite(result) or not 0 <= result <= 1_000_000_000:
        raise ValueError(f"{name} must be between 0 and 1,000,000,000")
    return result


def text(value, name, maximum=255):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must contain 1–{maximum} characters")
    return value.strip()


def password_value(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 1024:
        raise ValueError("Password must contain 1–1024 characters")
    return value


def require_program(program_id):
    row = query(PROGRAM_SELECT + " WHERE p.ProgramID = %s", (program_id,), one=True)
    if row is None:
        abort(404, description="Program not found")
    return row


def page_limit():
    return min(integer(request.args.get("limit", 200), "limit"), 1000)


def recommendations(user_id, max_tuition, min_salary):
    """Use only the preferred major and explicit constraints; no silent fallback."""
    sql = (
        PROGRAM_SELECT
        + """
        WHERE p.MajorID = (SELECT PreferredMajor FROM User WHERE UserID = %s)
          AND u.Tuition <= %s AND p.MedianSalary >= %s
        ORDER BY p.MedianSalary DESC, p.ProgramID LIMIT 200
    """
    )
    rows = query(sql, (user_id, max_tuition, min_salary))
    if rows:
        average = query(
            """SELECT AVG(u.Tuition) AS value FROM Program p
            JOIN University u ON p.UniversityID = u.UniversityID WHERE p.MajorID = %s""",
            (rows[0]["MajorID"],),
            one=True,
        )
        for row in rows:
            row["AvgTuitionForMajor"] = average["value"]
    return rows


def register(app):
    # Preserve the original template endpoint names.
    for path, endpoint, template in [
        ("/", "index", "index.html"),
        ("/login", "login_page", "login.html"),
        ("/admin", "admin", "admin.html"),
        ("/alert", "alert_page", "alert.html"),
        ("/userinfo", "userinfo_page", "userinfo.html"),
    ]:
        app.add_url_rule(path, endpoint, lambda template=template: render_template(template))

    @app.get("/api/session")
    def session_info():
        from . import csrf_token

        return jsonify(user_id=session.get("user_id"), csrf_token=csrf_token())

    @app.post("/api/login")
    def login_user():
        data = body()
        username = text(data.get("username"), "username")
        password = password_value(data.get("password"))
        row = query(
            "SELECT UserID, Username, PasswordHash, IsAdmin FROM User WHERE Username = %s",
            (username,),
            one=True,
        )
        if not row or not check_password_hash(row["PasswordHash"], password):
            return jsonify(status="fail", error="Invalid username or password"), 401
        session.clear()
        session["user_id"] = row["UserID"]
        session.permanent = True
        from . import csrf_token

        return jsonify(
            status="success",
            user_id=row["UserID"],
            username=row["Username"],
            is_admin=bool(row["IsAdmin"]),
            csrf_token=csrf_token(),
        )

    @app.post("/api/logout")
    def logout():
        session.clear()
        return jsonify(status="ok")

    @app.get("/api/data-source")
    def data_source():
        manifest = Path(app.root_path).parent / "data" / "processed" / "manifest.json"
        return jsonify(json.loads(manifest.read_text(encoding="utf-8")))

    @app.get("/api/programs")
    @app.get("/api/programs/search")
    @app.get("/api/programs/keyword-search")
    @app.get("/api/programs/filter")
    @app.get("/api/programs/by-university")
    def programs():
        clauses, values = ["1=1"], []
        args = request.args
        if request.path.endswith("keyword-search") and not args.get("q", "").strip():
            raise ValueError("q is required")
        if request.path.endswith("by-university") and not args.get("university_name"):
            raise ValueError("university_name is required")
        if request.path.endswith("/filter") and not all(
            k in args for k in ("max_tuition", "min_salary")
        ):
            raise ValueError("max_tuition and min_salary are required")
        if args.get("q", "").strip():
            clauses.append(
                "(p.Name LIKE %s OR m.MajorName LIKE %s OR u.Name LIKE %s OR u.Location LIKE %s)"
            )
            values.extend(["%" + text(args["q"], "q") + "%"] * 4)
        for key, column in [
            ("major", "m.MajorName"),
            ("location", "u.Location"),
            ("university_name", "u.Name"),
        ]:
            if args.get(key):
                # Partial major names match official CIP descriptions, e.g. Computer Science.
                clauses.append(f"{column} LIKE %s")
                values.append("%" + text(args[key], key) + "%")
        for key, column, operator in [
            ("max_tuition", "u.Tuition", "<="),
            ("min_salary", "p.MedianSalary", ">="),
        ]:
            if key in args:
                clauses.append(f"{column} {operator} %s")
                values.append(amount(args[key], key))
        return jsonify(
            query(
                PROGRAM_SELECT
                + " WHERE "
                + " AND ".join(clauses)
                + " ORDER BY p.ProgramID LIMIT %s",
                (*values, page_limit()),
            )
        )

    @app.get("/api/programs/<int:program_id>")
    def get_program(program_id):
        return jsonify(require_program(program_id))

    @app.get("/api/programs/<int:program_id>/details")
    def program_details(program_id):
        require_program(program_id)
        return jsonify(
            query(
                """SELECT p.ProgramID, p.Name AS ProgramName,
            u.Name AS UniversityName, u.Location, m.MajorName, m.Field,
            j.JobID, j.JobTitle, j.Company, j.Location AS JobLocation, j.AvgSalary
            FROM Program p JOIN University u ON p.UniversityID=u.UniversityID
            JOIN Major m ON p.MajorID=m.MajorID
            LEFT JOIN MajorJob mj ON m.MajorID=mj.MajorID
            LEFT JOIN Job j ON mj.JobID=j.JobID WHERE p.ProgramID=%s""",
                (program_id,),
            )
        )

    def program_values(data, partial=False):
        validators = {
            "name": ("Name", text),
            "university_id": ("UniversityID", integer),
            "major_id": ("MajorID", integer),
            "degree_type": ("DegreeType", text),
            "median_salary": ("MedianSalary", lambda v, n: amount(v, n, optional=True)),
        }
        values = {}
        for key, (column, validate) in validators.items():
            if not partial or key in data:
                values[column] = validate(data.get(key), key)
        if not values:
            raise ValueError("No valid fields to update")
        return values

    @app.post("/api/programs")
    def create_program():
        values = program_values(body())
        values.update(Source="User supplied", EarningsMetric="User supplied; not Scorecard")
        program_id, _ = execute(
            "INSERT INTO Program ("
            + ",".join(values)
            + ") VALUES ("
            + ",".join(["%s"] * len(values))
            + ")",
            tuple(values.values()),
        )
        get_db().commit()
        return jsonify(require_program(program_id)), 201

    @app.put("/api/programs/<int:program_id>")
    def update_program(program_id):
        require_program(program_id)
        values = program_values(body(), partial=True)
        values.update(Source="User edited", EarningsMetric="User edited; verify original source")
        execute(
            "UPDATE Program SET "
            + ",".join(f"{key} = %s" for key in values)
            + " WHERE ProgramID = %s",
            (*values.values(), program_id),
        )
        get_db().commit()
        return jsonify(require_program(program_id))

    @app.delete("/api/programs/<int:program_id>")
    def delete_program(program_id):
        require_program(program_id)
        execute("DELETE FROM Program WHERE ProgramID = %s", (program_id,))
        get_db().commit()
        return jsonify(status="deleted")

    @app.get("/api/majors")
    def list_majors():
        return jsonify(query("SELECT MajorID, MajorName, CIPCode FROM Major ORDER BY MajorName"))

    @app.get("/api/jobs")
    def list_jobs():
        return jsonify(query("SELECT JobID, JobTitle FROM Job ORDER BY JobTitle"))

    @app.get("/api/majors/<major_name>/jobs")
    def jobs_for_major(major_name):
        return jsonify(
            query(
                """SELECT j.* FROM Job j JOIN MajorJob mj ON j.JobID=mj.JobID
            JOIN Major m ON m.MajorID=mj.MajorID WHERE m.MajorName=%s""",
                (major_name,),
            )
        )

    @app.get("/api/admin/major-jobs/<int:major_id>")
    def major_jobs(major_id):
        return jsonify(
            query(
                """SELECT j.JobID, j.JobTitle FROM Job j
            JOIN MajorJob mj ON j.JobID=mj.JobID WHERE mj.MajorID=%s""",
                (major_id,),
            )
        )

    @app.post("/api/admin/update-major-jobs")
    def update_major_jobs():
        data = body()
        major_id, job1, job2 = [integer(data.get(k), k) for k in ("major_id", "job1", "job2")]
        threshold = amount(data.get("threshold", 15000), "threshold")
        if job1 == job2:
            raise ValueError("Choose two different jobs")
        db = get_db()
        # The authorization SELECT may have started a MySQL read transaction.
        db.commit()
        db.start_transaction(isolation_level="SERIALIZABLE")
        jobs = query(
            "SELECT JobID, JobTitle, AvgSalary FROM Job WHERE JobID IN (%s,%s)", (job1, job2)
        )
        major = query("SELECT MajorName FROM Major WHERE MajorID=%s", (major_id,), one=True)
        linked = query(
            "SELECT JobID FROM MajorJob WHERE MajorID=%s AND JobID=%s", (major_id, job1), one=True
        )
        if len(jobs) != 2 or not major or not linked:
            raise ValueError("The major and both jobs must exist, and Job 1 must be linked")
        by_id = {row["JobID"]: row for row in jobs}
        average = query(
            """SELECT AVG(j.AvgSalary) AS salary FROM Job j
            JOIN MajorJob mj ON mj.JobID=j.JobID WHERE mj.MajorID=%s""",
            (major_id,),
            one=True,
        )["salary"]
        if average is None or any(row["AvgSalary"] is None for row in jobs):
            raise ValueError("Verified job salaries are required for this transaction")
        diff = abs(float(average) - float(by_id[job1]["AvgSalary"]))
        switched = diff > threshold
        if switched:
            execute(
                """DELETE FROM MajorJob WHERE MajorID=%s AND JobID IN
                (SELECT JobID FROM Job WHERE JobTitle=%s)""",
                (major_id, by_id[job1]["JobTitle"]),
            )
            for job in query("SELECT JobID FROM Job WHERE JobTitle=%s", (by_id[job2]["JobTitle"],)):
                if not query(
                    "SELECT JobID FROM MajorJob WHERE MajorID=%s AND JobID=%s",
                    (major_id, job["JobID"]),
                    one=True,
                ):
                    execute(
                        "INSERT INTO MajorJob (MajorID,JobID) VALUES (%s,%s)",
                        (major_id, job["JobID"]),
                    )
        db.commit()
        return jsonify(
            status="ok",
            switched=switched,
            threshold=threshold,
            diff_major_job1=diff,
            major={"id": major_id, "name": major["MajorName"], "avg_salary": average},
            job1={
                "id": job1,
                "title": by_id[job1]["JobTitle"],
                "avg_salary": by_id[job1]["AvgSalary"],
            },
            job2={
                "id": job2,
                "title": by_id[job2]["JobTitle"],
                "avg_salary": by_id[job2]["AvgSalary"],
            },
        )

    @app.route("/api/bookmarks", methods=["POST", "DELETE"])
    def bookmark():
        user_id = session["user_id"]
        program_id = integer(body().get("program_id"), "program_id")
        require_program(program_id)
        if request.method == "POST":
            # Ignore duplicate keys only; foreign-key violations must still fail.
            suffix = (
                " ON CONFLICT(UserID,ProgramID) DO NOTHING"
                if app.config["DATABASE_BACKEND"] == "sqlite"
                else " ON DUPLICATE KEY UPDATE ProgramID=VALUES(ProgramID)"
            )
            execute(
                "INSERT INTO Bookmark (UserID, ProgramID) VALUES (%s,%s)" + suffix,
                (user_id, program_id),
            )
        else:
            execute("DELETE FROM Bookmark WHERE UserID=%s AND ProgramID=%s", (user_id, program_id))
        get_db().commit()
        return jsonify(status="ok"), 201 if request.method == "POST" else 200

    @app.route("/api/users/<int:user_id>/bookmarks", methods=["GET", "DELETE"])
    def bookmarks(user_id):
        if request.method == "DELETE":
            _, count = execute("DELETE FROM Bookmark WHERE UserID=%s", (user_id,))
            get_db().commit()
            return jsonify(status="ok", deleted=count)
        return jsonify(
            query(
                PROGRAM_SELECT + " JOIN Bookmark b ON b.ProgramID=p.ProgramID WHERE b.UserID=%s",
                (user_id,),
            )
        )

    @app.get("/api/analytics/avg-salary-by-major")
    def average_salary():
        return jsonify(
            query("""SELECT m.MajorName, AVG(p.MedianSalary) AS AvgMedianSalary,
            COUNT(p.MedianSalary) AS ProgramsWithEarnings FROM Major m
            JOIN Program p ON p.MajorID=m.MajorID GROUP BY m.MajorID,m.MajorName
            ORDER BY AvgMedianSalary DESC""")
        )

    @app.get("/api/users/<int:user_id>/recommend")
    def recommend(user_id):
        max_tuition = amount(request.args.get("max_tuition", 999999), "max_tuition")
        min_salary = amount(request.args.get("min_salary", 60000), "min_salary")
        if app.config["DATABASE_BACKEND"] == "mysql":
            cursor = get_db().cursor(dictionary=True)
            try:
                cursor.callproc("RecommendProgramsForUser", [user_id, max_tuition, min_salary])
                rows = []
                for result in cursor.stored_results():
                    rows.extend(result.fetchall())
                return jsonify(rows)
            finally:
                cursor.close()
        return jsonify(recommendations(user_id, max_tuition, min_salary))

    @app.get("/api/comparisons/<int:user_id>")
    def comparisons(user_id):
        return jsonify(
            query(
                """SELECT c.ComparisonID,c.NoteFromUser,c.ProgramID1,c.ProgramID2,
            p1.Name AS Program1Name,p2.Name AS Program2Name FROM Comparison c
            JOIN Program p1 ON c.ProgramID1=p1.ProgramID JOIN Program p2 ON c.ProgramID2=p2.ProgramID
            WHERE c.UserID=%s ORDER BY c.ComparisonID DESC""",
                (user_id,),
            )
        )

    @app.post("/api/comparisons")
    def save_comparison():
        data = body()
        p1 = integer(data.get("program1_id"), "program1_id")
        p2 = integer(data.get("program2_id"), "program2_id")
        if p1 == p2:
            raise ValueError("Select two different programs")
        note = data.get("note", "")
        if not isinstance(note, str) or len(note) > 2000:
            raise ValueError("note must be at most 2000 characters")
        execute(
            "INSERT INTO Comparison (UserID,ProgramID1,ProgramID2,NoteFromUser) VALUES (%s,%s,%s,%s)",
            (session["user_id"], p1, p2, note),
        )
        get_db().commit()
        return jsonify(status="Comparison saved"), 201

    @app.delete("/api/comparisons/<int:comparison_id>")
    def delete_comparison(comparison_id):
        _, count = execute(
            "DELETE FROM Comparison WHERE ComparisonID=%s AND UserID=%s",
            (comparison_id, session["user_id"]),
        )
        if not count:
            abort(404, description="Comparison not found")
        get_db().commit()
        return jsonify(status="deleted")

    @app.get("/api/users/<int:user_id>/alerts")
    def alerts(user_id):
        return jsonify(
            query(
                "SELECT AlertID,UserID,Message FROM Alert WHERE UserID=%s ORDER BY AlertID DESC",
                (user_id,),
            )
        )

    @app.delete("/api/users/<int:user_id>/alerts/<int:alert_id>")
    def delete_alert(user_id, alert_id):
        _, count = execute("DELETE FROM Alert WHERE UserID=%s AND AlertID=%s", (user_id, alert_id))
        if not count:
            abort(404, description="Alert not found")
        get_db().commit()
        return jsonify(status="deleted")

    @app.get("/api/users/<int:user_id>/info")
    def user_info(user_id):
        row = query(
            """SELECT u.UserID,u.Username,u.Email,u.PreferredLocation,
            u.PreferredMajor AS PreferredMajorID,m.MajorName AS PreferredMajor,
            u.PreferredJob AS PreferredJobID,j.JobTitle AS PreferredJob FROM User u
            LEFT JOIN Major m ON u.PreferredMajor=m.MajorID
            LEFT JOIN Job j ON u.PreferredJob=j.JobID WHERE u.UserID=%s""",
            (user_id,),
            one=True,
        )
        return jsonify(row)

    @app.put("/api/users/<int:user_id>/password")
    def update_password(user_id):
        password = password_value(body().get("new_password"))
        if len(password) < 12:
            raise ValueError("Use a password of at least 12 characters")
        execute(
            "UPDATE User SET PasswordHash=%s WHERE UserID=%s",
            (generate_password_hash(password), user_id),
        )
        get_db().commit()
        return jsonify(status="password_updated")

    @app.route("/api/users/<int:user_id>/preferences", methods=["POST", "PUT"])
    def preferences(user_id):
        data = body()
        major = integer(
            data.get("preferred_major", data.get("preferred_major_id")),
            "preferred_major",
            optional=True,
        )
        job = integer(
            data.get("preferred_job", data.get("preferred_job_id")), "preferred_job", optional=True
        )
        execute(
            "UPDATE User SET PreferredMajor=%s, PreferredJob=%s WHERE UserID=%s",
            (major, job, user_id),
        )
        get_db().commit()
        return jsonify(status="updated")
