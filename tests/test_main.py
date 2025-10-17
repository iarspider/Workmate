import sys
from pathlib import Path

import pytest

import main


# -------------------------
# Helpers
# -------------------------
def write_csv(path: Path, rows):
    path.write_text(
        "brand,rating\n" + "\n".join(f"{r['brand']},{r['rating']}" for r in rows),
        encoding="utf-8",
    )
    return path


# -------------------------
# report() decorator
# -------------------------
def test_report_registers_functions():
    assert (
        "average-rating" in main.reports
    )  # registered by @report(name="...") in main.py

    # register another report
    @main.report
    def demo(_):
        return "ok"

    assert "demo" in main.reports
    assert main.reports["demo"] is demo


def test_report_registers_with_name_override():
    @main.report(name="custom")
    def demo2(_):
        return "ok2"

    assert "custom" in main.reports
    assert main.reports["custom"] is demo2


# -------------------------
# load_files
# -------------------------
def test_load_files_reads_multiple_csvs(tmp_path: Path):
    f1 = write_csv(
        tmp_path / "a.csv",
        [{"brand": "Foo", "rating": "4.0"}, {"brand": "Foo", "rating": "5.0"}],
    )
    f2 = write_csv(
        tmp_path / "b.csv",
        [{"brand": "Baz", "rating": "3.0"}],
    )

    rows = main.load_files([str(f1), str(f2)])
    assert len(rows) == 3
    # DictReader returns strings as in main.load_files
    assert rows[0]["brand"] == "Foo" and rows[0]["rating"] == "4.0"


# -------------------------
# average_rating
# -------------------------
def test_average_rating_aggregates_and_sorts_descending():
    data = [
        {"brand": "Foo", "rating": "4.0"},
        {"brand": "Foo", "rating": "5.0"},
        {"brand": "Baz", "rating": "3.0"},
        {"brand": "Zeta", "rating": "4.25"},
    ]
    rows = main.average_rating(data)

    # Expected averages: Foo=4.5, Zeta=4.25, Baz=3.0
    assert [r["brand"] for r in rows] == ["Foo", "Zeta", "Baz"]
    assert rows[0]["rating"] == pytest.approx(4.5)
    assert rows[1]["rating"] == pytest.approx(4.25)
    assert rows[2]["rating"] == pytest.approx(3.0)

    # Index column starts from 1
    assert rows[0][""] == 1 and rows[1][""] == 2 and rows[2][""] == 3


# -------------------------
# print_report
# -------------------------
def test_print_report_formats_psql_table(capsys):
    rows = [
        {"": 1, "brand": "Foo", "rating": 4.5},
        {"": 2, "brand": "Zeta", "rating": 4.25},
    ]
    main.print_report(rows)

    out = capsys.readouterr().out
    # basic structure checks; we don't snapshot full table to avoid coupling to tabulate version
    assert "+---" in out and "|  " in out  # psql grid
    assert "brand" in out and "rating" in out
    assert "Foo" in out and "Zeta" in out


# -------------------------
# CLI smoke test
# -------------------------
def test_cli_integration_smoke(tmp_path: Path, monkeypatch, capsys):
    f1 = write_csv(
        tmp_path / "brands1.csv",
        [{"brand": "Foo", "rating": "4.0"}, {"brand": "Foo", "rating": "5.0"}],
    )
    f2 = write_csv(
        tmp_path / "brands2.csv",
        [{"brand": "Baz", "rating": "3.0"}],
    )

    argv = [
        "workmate",
        "--files",
        str(f1),
        str(f2),
        "--report",
        "average-rating",
    ]
    monkeypatch.setenv("PYTHONUTF8", "1")
    monkeypatch.setattr(sys, "argv", argv)

    # Run main; it will parse args, load files, run report, and print the table.
    main.main()

    out = capsys.readouterr().out
    # Ensure brands are present and Foo (avg 4.5) appears in output
    assert "Foo" in out and "Baz" in out
    # Ensure 4.5 is present
    assert "4.5" in out
