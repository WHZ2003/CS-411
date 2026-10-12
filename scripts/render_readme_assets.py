"""Generate dependency-free README SVGs from the committed Scorecard snapshot.

Run: python scripts/render_readme_assets.py
All counts are computed from repository data; no network or plotting packages needed.
"""

import csv
import json
import math
from collections import Counter
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "processed"
OUT = ROOT / "docs" / "assets"
INK = "#14233b"
MUTED = "#536780"
TEAL = "#007e80"
BLUE = "#5368d4"
PALE = "#e7edf5"
FONT = "Segoe UI, Inter, Arial, sans-serif"


def label(x, y, value, size=18, color=INK, weight=400, anchor="start"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}" text-anchor="{anchor}">{escape(str(value))}</text>'
    )


def rect(x, y, width, height, fill, radius=0):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}"/>'


def write_svg(name, height, title, description, shapes, background="#f7f9fc"):
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" '
        f'viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">'
        f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>'
        f'<g font-family="{FONT}">{rect(0, 0, 1200, height, background, 24)}'
        + "".join(shapes)
        + "</g></svg>\n"
    )
    (OUT / name).write_text(svg, encoding="utf-8", newline="\n")


def banner(counts):
    shapes = [
        '<defs><linearGradient id="glow" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#19c2b8"/><stop offset="100%" stop-color="#647cf5"/>'
        "</linearGradient></defs>",
        '<circle cx="1110" cy="30" r="220" fill="#172e4d"/>',
        '<circle cx="1110" cy="30" r="140" fill="#1b3953"/>',
        rect(48, 42, 6, 22, "#47d8c5", 3),
        label(70, 59, "UIUC CS 411  /  FALL 2025  /  TEAM HAJIMI", 15, "#b8c9df", 600),
        label(48, 144, "EduConnect", 66, "#ffffff", 700),
        label(50, 186, "Find your program. Understand the trade-offs.", 25, "#d3e0ef"),
        label(
            50,
            225,
            "Explore universities, compare costs and earnings, and build your shortlist.",
            18,
            "#a7bdd4",
        ),
    ]
    for x, value, name in [
        (48, counts["universities"], "INSTITUTIONS"),
        (330, counts["majors"], "MAJOR CATEGORIES"),
        (612, counts["programs"], "BACHELOR'S RECORDS"),
    ]:
        shapes += [
            rect(x, 270, 264, 100, "#172b45", 14),
            label(x + 22, 314, f"{value:,}", 32, "#ffffff", 700),
            label(x + 22, 344, name, 12, "#a7bdd4", 600),
        ]
    # A small abstract relational graph, not a chart of invented observations.
    shapes.append(
        '<path d="M976 137L1108 198L992 291Z" fill="none" stroke="#6985a9" stroke-width="2"/>'
    )
    for x, y, radius in [(976, 137, 22), (1108, 198, 34), (992, 291, 18)]:
        shapes.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="url(#glow)"/>')
    shapes.append(label(976, 354, "REAL DATA", 14, "#6fe6d4", 700))
    write_svg(
        "hero.svg",
        410,
        "EduConnect — College and Program Explorer",
        "UIUC CS 411. Real College Scorecard snapshot: "
        f"{counts['universities']:,} institutions, {counts['majors']:,} major categories, "
        f"{counts['programs']:,} bachelor's records. Pinned 2025 releases.",
        shapes,
        "#0d1c31",
    )


def earnings_chart(status):
    total = sum(status.values())
    parts = [
        ("Reported", status["reported"], TEAL),
        ("Privacy-suppressed", status["PrivacySuppressed"], BLUE),
        ("Unavailable", status["NULL"], "#8092ad"),
    ]
    shapes = [
        label(44, 48, "HOW MUCH EARNINGS DATA IS AVAILABLE?", 14, MUTED, 600),
        label(44, 88, "Coverage, with the gaps left visible", 29, INK, 700),
    ]
    circumference = 2 * math.pi * 100
    offset = 0
    for name, count, color in parts:
        length = count / total * circumference
        shapes.append(
            f'<circle cx="208" cy="245" r="100" fill="none" stroke="{color}" '
            f'stroke-width="30" stroke-dasharray="{length:.4f} {circumference - length:.4f}" '
            f'stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 208 245)"/>'
        )
        offset += length
    shapes += [
        label(208, 244, f"{status['reported'] / total:.1%}", 42, INK, 700, "middle"),
        label(208, 274, "reported earnings", 16, MUTED, anchor="middle"),
    ]
    for i, (name, count, color) in enumerate(parts):
        y = 162 + i * 77
        shapes += [
            rect(416, y - 16, 14, 14, color, 4),
            label(444, y, name, 21, INK, 600),
            label(1118, y, f"{count:,}  ·  {count / total:.1%}", 22, INK, 600, "end"),
            rect(444, y + 14, 674, 7, PALE, 3),
            rect(444, y + 14, round(674 * count / total, 2), 7, color, 3),
        ]
    shapes += [
        label(
            44,
            402,
            f"{total:,} program records · EARN_MDN_HI_2YR · pinned 2025 field-of-study release",
            15,
            MUTED,
        ),
        label(
            44,
            430,
            "Suppressed and unavailable values stay NULL. No estimated earnings are inserted.",
            16,
            MUTED,
        ),
    ]
    description = "; ".join(f"{name}: {count:,} ({count / total:.1%})" for name, count, _ in parts)
    write_svg("earnings-coverage.svg", 462, "Reported earnings coverage", description, shapes)


def state_chart(institutions, programs):
    school_states = {row["UniversityID"]: row["Location"] for row in institutions}
    state_counts = Counter(school_states[row["UniversityID"]] for row in programs)
    leaders = sorted(state_counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    names = {
        "CA": "California",
        "NY": "New York",
        "PA": "Pennsylvania",
        "TX": "Texas",
        "OH": "Ohio",
        "IL": "Illinois",
        "MA": "Massachusetts",
        "FL": "Florida",
        "NC": "North Carolina",
        "MI": "Michigan",
        "VA": "Virginia",
        "MO": "Missouri",
        "IN": "Indiana",
        "TN": "Tennessee",
        "MN": "Minnesota",
        "WI": "Wisconsin",
    }
    maximum = math.ceil(leaders[0][1] / 1000) * 1000
    start, width = 260, 820
    shapes = [
        label(44, 48, "WHERE THE SNAPSHOT HAS THE MOST PROGRAM RECORDS", 14, MUTED, 600),
        label(44, 88, "A national catalog, viewed by state", 29, INK, 700),
        label(
            44,
            120,
            "Top 10 states by matched bachelor's program records — not a ranking of school quality",
            17,
            MUTED,
        ),
    ]
    for tick in range(0, maximum + 1, 1000):
        x = start + width * tick / maximum
        shapes += [
            f'<path d="M{x} 155V593" stroke="#dce4ef" stroke-width="1"/>',
            label(x, 620, f"{tick:,}", 13, MUTED, anchor="middle"),
        ]
    for i, (state, count) in enumerate(leaders):
        y = 161 + i * 44
        bar_width = width * count / maximum
        shapes += [
            label(235, y + 21, names.get(state, state), 18, INK, anchor="end"),
            rect(start, y, round(bar_width, 2), 29, TEAL if state == "IL" else BLUE, 5),
            label(round(start + bar_width + 12, 2), y + 21, f"{count:,}", 16, INK, 600),
        ]
    shapes += [
        label(
            44,
            666,
            "Unit: institution × four-digit CIP field × bachelor's credential. Illinois is highlighted when present.",
            15,
            MUTED,
        ),
        label(
            44,
            691,
            "Computed from the committed universities.csv and programs.csv; includes records without reported earnings.",
            15,
            MUTED,
        ),
    ]
    description = "; ".join(f"{names.get(state, state)}: {count:,}" for state, count in leaders)
    write_svg(
        "programs-by-state.svg", 724, "Top ten states by program record count", description, shapes
    )
    return leaders


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    with (DATA / "universities.csv").open(encoding="utf-8", newline="") as file:
        institutions = list(csv.DictReader(file))
    with (DATA / "programs.csv").open(encoding="utf-8", newline="") as file:
        programs = list(csv.DictReader(file))
    assert len(institutions) == manifest["counts"]["universities"]
    assert len(programs) == manifest["counts"]["programs"]
    assert sum(manifest["earnings_status"].values()) == len(programs)
    assert (
        sum(bool(row["MedianSalary"]) for row in programs)
        == manifest["earnings_status"]["reported"]
    )
    banner(manifest["counts"])
    earnings_chart(manifest["earnings_status"])
    leaders = state_chart(institutions, programs)
    print("Generated hero.svg, earnings-coverage.svg, programs-by-state.svg")
    print("State counts:", dict(leaders))


if __name__ == "__main__":
    main()
