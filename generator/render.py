"""Render the bio site into a directory of static files.

The site is built once, at image build time. There is no runtime: nginx just
serves whatever this produced, so whichever bio files exist when the container
is built are exactly the bios on the site.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from .bios import Bio, Problem, load_bios
from .config import SiteConfig, Team

PACKAGE_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = PACKAGE_ROOT / "templates"
STATIC_DIR = PACKAGE_ROOT / "static"


class BuildError(Exception):
    """Raised when a build is asked to proceed despite invalid bio files."""


@dataclass(frozen=True, slots=True)
class TeamGroup:
    """A team plus its bios. Teams with no bios yet still render, as an empty slot."""

    team: Team
    bios: tuple[Bio, ...]

    @property
    def count(self) -> int:
        return len(self.bios)


@dataclass(frozen=True, slots=True)
class BuildResult:
    out_dir: Path
    bios: int
    pages: int
    problems: tuple[Problem, ...]


def group_by_team(config: SiteConfig, bios: tuple[Bio, ...]) -> tuple[TeamGroup, ...]:
    """Group bios in ``site.yml`` team order."""
    buckets: dict[str, list[Bio]] = {team.name: [] for team in config.teams}
    for bio in bios:
        buckets.setdefault(bio.team, []).append(bio)
    return tuple(
        TeamGroup(team=team, bios=tuple(buckets.get(team.name, ())))
        for team in config.teams
    )


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(default=True, default_for_string=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build(bios_dir: Path, config: SiteConfig, out_dir: Path, *, strict: bool = True) -> BuildResult:
    """Build the whole site. Invalid bio files fail the build unless ``strict`` is off."""
    bios, problems = load_bios(bios_dir, config)
    if problems and strict:
        raise BuildError("\n".join(str(problem) for problem in problems))

    groups = group_by_team(config, bios)
    env = _environment()
    built_at = datetime.now(timezone.utc)
    shared = {
        "site": config,
        "built_at": built_at,
        "built_at_label": built_at.strftime("%d %b %Y, %H:%M UTC"),
        "stats": {
            "bios": len(bios),
            "teams": sum(1 for group in groups if group.count),
            "total_teams": len(groups),
        },
    }

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    pages = 0
    _write(out_dir / "index.html", env.get_template("index.html.j2").render(**shared, bios=bios, groups=groups))
    pages += 1
    _write(out_dir / "404.html", env.get_template("404.html.j2").render(**shared))
    pages += 1

    bio_template = env.get_template("bio.html.j2")
    by_team = {group.team.name: group for group in groups}
    for bio in bios:
        group = by_team.get(bio.team)
        teammates = tuple(other for other in (group.bios if group else ()) if other.slug != bio.slug)
        _write(
            out_dir / bio.slug / "index.html",
            bio_template.render(**shared, bio=bio, team=group.team if group else None, teammates=teammates),
        )
        pages += 1

    if STATIC_DIR.is_dir():
        shutil.copytree(STATIC_DIR, out_dir / "assets", dirs_exist_ok=True)

    return BuildResult(out_dir=out_dir, bios=len(bios), pages=pages, problems=problems)
