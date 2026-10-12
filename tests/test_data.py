import csv
import hashlib
import io
import json
import zipfile

import pytest

from educonnect.cli import import_snapshot
from educonnect.db import execute, get_db, query
from scripts.prepare_scorecard import number, prepare


@pytest.mark.parametrize("value", [None, "", "NULL", "PrivacySuppressed", "NA"])
def test_missing_numbers_are_not_zero(value):
    assert number(value) is None


@pytest.mark.parametrize("value", ["NaN", "-1", "inf", "nonsense"])
def test_invalid_numbers_rejected(value):
    with pytest.raises(ValueError):
        number(value)


def test_snapshot_integrity(snapshot_dir):
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["normalized_sha256"].items():
        assert hashlib.sha256((snapshot_dir / name).read_bytes()).hexdigest() == expected
    with (snapshot_dir / "programs.csv").open(encoding="utf-8", newline="") as f:
        programs = list(csv.DictReader(f))
    assert len(programs) == manifest["counts"]["programs"]
    assert len({p["SourceKey"] for p in programs}) == len(programs)
    assert any(p["MedianSalary"] == "" for p in programs)
    assert any(
        p["UniversityID"] == "145637" and p["MajorID"] == "1107" for p in programs
    )  # UIUC CS


def test_real_import_repeatable_and_keeps_user_edits(app, snapshot_dir):
    with app.app_context():
        counts = import_snapshot(snapshot_dir)
        assert counts["Program"] > 60000
        program = query("SELECT ProgramID FROM Program WHERE SourceKey='145637:1107:3'", one=True)
        pid = program["ProgramID"]
        execute("INSERT INTO Bookmark (UserID,ProgramID) VALUES (1,%s)", (pid,))
        execute(
            "UPDATE Program SET Name='Curated name', Source='User edited' WHERE ProgramID=%s",
            (pid,),
        )
        get_db().commit()
        before = query("SELECT COUNT(*) AS n FROM Program", one=True)["n"]
        import_snapshot(snapshot_dir)
        assert query("SELECT COUNT(*) AS n FROM Program", one=True)["n"] == before
        assert (
            query("SELECT Name FROM Program WHERE ProgramID=%s", (pid,), one=True)["Name"]
            == "Curated name"
        )
        assert query(
            "SELECT ProgramID FROM Bookmark WHERE UserID=1 AND ProgramID=%s", (pid,), one=True
        )


def zip_csv(path, rows):
    text = io.StringIO()
    writer = csv.DictWriter(text, list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("source.csv", text.getvalue())


def test_normalization_filters_degrees_preserves_cip_and_null(tmp_path):
    zip_csv(
        tmp_path / "institution.zip",
        [
            dict(
                UNITID="100",
                INSTNM="Real source-shaped fixture",
                STABBR="IL",
                CITY="City",
                TUITIONFEE_IN="0",
                TUITIONFEE_OUT="NULL",
                INSTURL="example.invalid",
            )
        ],
    )
    base = dict(
        UNITID="100",
        CIPCODE="0100",
        CIPDESC="Agriculture, General.",
        CREDLEV="3",
        CREDDESC="Bachelors Degree",
        EARN_MDN_HI_2YR="PrivacySuppressed",
    )
    zip_csv(
        tmp_path / "field-of-study.zip", [base, dict(base, CREDLEV="5"), dict(base, UNITID="999")]
    )
    manifest = prepare(tmp_path, tmp_path / "output")
    assert manifest["counts"] == {"universities": 1, "majors": 1, "programs": 1}
    assert manifest["earnings_status"]["PrivacySuppressed"] == 1
    assert manifest["excluded_rows"]["not_bachelors"] == 1
    assert ",0100\n" in (tmp_path / "output/majors.csv").read_text()


def test_import_failure_is_atomic(app, snapshot_dir, tmp_path):
    # Valid first table followed by invalid schema must roll back the first write.
    (tmp_path / "universities.csv").write_text(
        "UniversityID,Name,Location,City,Tuition,TuitionOutState,Website,Source\n999999,Transient,IL,City,1,2,example.invalid,Test\n"
    )
    (tmp_path / "majors.csv").write_text("Unexpected\nvalue\n")
    with app.app_context():
        with pytest.raises(ValueError):
            import_snapshot(tmp_path)
        assert (
            query("SELECT UniversityID FROM University WHERE UniversityID=999999", one=True) is None
        )
