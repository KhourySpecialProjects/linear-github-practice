#!/usr/bin/env python3
"""Turn a class roster CSV into the pre-class artifacts for the bio exercise.

Run this from the repository root, before class, to produce (a) one Linear issue
per student and (b) the pre-assigned review ring. Every student then has an
issue that already names their file, their team, and the person who will review
their pull request, so nobody spends class time hunting for a reviewer.

The roster CSV needs the header ``name,github,team``. ``team`` may be blank or
omitted entirely; blank lines, stray whitespace and a UTF-8 BOM are tolerated.

    name,github,team
    Jane Doe,janedoe,Team Falcon

Usage examples::

    # Paste-ready Linear issues, one block per student
    python scripts/roster.py roster.csv

    # Same thing as Markdown, to drop into a planning doc
    python scripts/roster.py roster.csv --format markdown

    # Just the review ring: who reviews whom
    python scripts/roster.py roster.csv --ring

    # Check the filenames students will be asked to create
    python scripts/roster.py roster.csv --slug-only

    # Machine-readable, for a Linear import script
    python scripts/roster.py roster.csv --format json > issues.json

The review ring is built from the roster sorted by name: student *n* reviews
student *n+1*, and the last student reviews the first.

Exit codes: ``0`` on success, ``2`` on a roster or environment problem.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

#: Exit code for "your roster or your checkout is wrong", never for bad output.
SETUP_ERROR = 2


def die(message: str) -> NoReturn:
    """Print an actionable error and stop with the setup exit code."""
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(SETUP_ERROR)


try:
    # Imported (rather than reimplemented) so the filenames printed here are
    # exactly the ones `python -m generator validate` will demand.
    from generator.text import slugify
except ImportError:
    # Run the script directly and Python puts scripts/ on sys.path, not the
    # repository root, so point it at the root this file lives in and retry.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    try:
        from generator.text import slugify
    except ImportError as exc:  # pragma: no cover - environment guard
        die(
            f"could not import 'generator.text' ({exc}). "
            "Run this script from a checkout of the repository, e.g. "
            "'python scripts/roster.py roster.csv' at the repository root."
        )

QUICKSTART = "docs/student-quickstart.md"
TEMPLATE = "bios/TEMPLATE.md"

FIELDS = (
    "name",
    "slug",
    "file",
    "team",
    "github",
    "reviewer",
    "reviewer_github",
    "issue_title",
    "issue_description",
)


@dataclass(frozen=True, slots=True)
class Student:
    name: str
    github: str
    team: str


def read_roster(path: Path) -> list[Student]:
    """Read the roster CSV, tolerating a BOM, blank lines and padded cells."""
    try:
        # utf-8-sig strips the BOM Excel likes to add.
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        die(f"could not read {path} - {exc}")

    reader = csv.DictReader(text.splitlines())
    if reader.fieldnames is None:
        die(f"{path} is empty - it needs the header 'name,github,team'")

    headers = {(field or "").strip().lower(): field for field in reader.fieldnames}
    if "name" not in headers:
        found = ", ".join(reader.fieldnames)
        die(f"{path} needs a 'name' column in its header (found: {found})")

    def cell(row: dict[str, str], key: str) -> str:
        field = headers.get(key)
        if field is None:
            return ""
        return (row.get(field) or "").strip()

    students: list[Student] = []
    for row in reader:
        name = cell(row, "name")
        if not name:
            continue  # blank line, or a trailing comma-only row
        students.append(Student(name=name, github=cell(row, "github"), team=cell(row, "team")))
    return students


def describe(student: Student, slug: str, reviewer: Student) -> str:
    """The ready-to-paste Linear issue description for one student."""
    team_line = f"- **Team:** {student.team}" if student.team else "- **Team:** ask your instructor"
    reviewer_handle = f" (@{reviewer.github})" if reviewer.github else ""
    return "\n".join(
        (
            f"Add your professional bio to the site as `bios/{slug}.md`.",
            "",
            f"- **File to create:** `bios/{slug}.md` (the filename must match your name exactly)",
            team_line,
            f"- **Your reviewer:** {reviewer.name}{reviewer_handle}",
            "",
            "Steps:",
            "",
            "1. Move this issue to In Progress and use **Copy git branch name** for your branch.",
            f"2. Copy `{TEMPLATE}` to `bios/{slug}.md` and fill it in.",
            "3. Run `python -m generator validate` until it passes, then push and open a pull request into `testing`.",
            f"4. Ask {reviewer.name} for the approving review, then squash-merge.",
            "",
            f"Walkthrough: `{QUICKSTART}` · Field reference: `{TEMPLATE}`",
        )
    )


def build_records(students: list[Student]) -> list[dict[str, str]]:
    """Sort the roster, close the review ring, and expand each student."""
    if not students:
        die("the roster is empty - add at least one 'name,github,team' row")

    ordered = sorted(students, key=lambda student: student.name.casefold())
    if len(ordered) == 1:
        print(
            f"warning: only one student on the roster, so {ordered[0].name} is their own reviewer",
            file=sys.stderr,
        )

    records: list[dict[str, str]] = []
    slugs: dict[str, str] = {}
    for index, student in enumerate(ordered):
        reviewer = ordered[(index + 1) % len(ordered)]
        slug = slugify(student.name)
        if "-" not in slug:
            print(
                f"warning: {student.name!r} slugs to {slug!r}, which the validator rejects "
                "- bio filenames need at least two name parts",
                file=sys.stderr,
            )
        if slug in slugs:
            print(
                f"warning: {student.name!r} and {slugs[slug]!r} both slug to {slug!r} "
                f"- they cannot both add bios/{slug}.md",
                file=sys.stderr,
            )
        else:
            slugs[slug] = student.name
        records.append(
            {
                "name": student.name,
                "slug": slug,
                "file": f"bios/{slug}.md",
                "team": student.team,
                "github": student.github,
                "reviewer": reviewer.name,
                "reviewer_github": reviewer.github,
                "issue_title": f"Add bio for {student.name}",
                "issue_description": describe(student, slug, reviewer),
            }
        )
    return records


def project(records: list[dict[str, str]], fields: tuple[str, ...]) -> list[dict[str, str]]:
    return [{field: record[field] for field in fields} for record in records]


def render_table(rows: list[dict[str, str]], fields: tuple[str, ...], headers: tuple[str, ...]) -> str:
    widths = [
        max(len(header), *(len(row[field]) for row in rows)) if rows else len(header)
        for field, header in zip(fields, headers)
    ]
    lines = [
        "  ".join(header.ljust(width) for header, width in zip(headers, widths)).rstrip(),
        "  ".join("-" * width for width in widths),
    ]
    lines.extend(
        "  ".join(row[field].ljust(width) for field, width in zip(fields, widths)).rstrip() for row in rows
    )
    return "\n".join(lines)


def render_markdown_table(rows: list[dict[str, str]], fields: tuple[str, ...], headers: tuple[str, ...]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    lines.extend("| " + " | ".join(row[field] for field in fields) + " |" for row in rows)
    return "\n".join(lines)


def render_csv(rows: list[dict[str, str]], fields: tuple[str, ...]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(fields), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().rstrip("\n")


def render_issues_text(rows: list[dict[str, str]]) -> str:
    blocks = []
    for row in rows:
        blocks.append(
            "\n".join(
                (
                    "=" * 72,
                    row["issue_title"],
                    "=" * 72,
                    row["issue_description"],
                )
            )
        )
    return "\n\n".join(blocks)


def render_issues_markdown(rows: list[dict[str, str]]) -> str:
    return "\n\n".join(f"## {row['issue_title']}\n\n{row['issue_description']}" for row in rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/roster.py",
        description=(
            "Expand a class roster CSV into Linear issues and the pre-assigned review ring "
            "for the bio-aggregator exercise. Run it from the repository root."
        ),
        epilog=(
            "examples:\n"
            "  python scripts/roster.py roster.csv\n"
            "  python scripts/roster.py roster.csv --format markdown\n"
            "  python scripts/roster.py roster.csv --ring\n"
            "  python scripts/roster.py roster.csv --slug-only\n"
            "  python scripts/roster.py roster.csv --format json > issues.json\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("roster", type=Path, help="roster CSV with the header 'name,github,team'")
    parser.add_argument(
        "--format",
        choices=("text", "markdown", "csv", "json"),
        default="text",
        help="output format (default: text)",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--ring",
        action="store_true",
        help="print only the review ring: each student and the peer who reviews their pull request",
    )
    mode.add_argument(
        "--slug-only",
        action="store_true",
        help="print only 'name,slug', to check the bio filenames students will need",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records = build_records(read_roster(args.roster))

    if args.ring:
        fields, headers = ("name", "reviewer"), ("Author", "Reviewer")
    elif args.slug_only:
        fields, headers = ("name", "slug"), ("Name", "Slug")
    else:
        fields, headers = FIELDS, FIELDS

    rows = project(records, fields)

    if args.format == "json":
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    elif args.format == "csv":
        print(render_csv(rows, fields))
    elif args.ring or args.slug_only:
        renderer = render_markdown_table if args.format == "markdown" else render_table
        print(renderer(rows, fields, headers))
    elif args.format == "markdown":
        print(render_issues_markdown(rows))
    else:
        print(render_issues_text(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
