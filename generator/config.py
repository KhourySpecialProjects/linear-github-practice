"""Instructor-owned site configuration (``site.yml``).

Students never edit this file, which is why the team list can be validated
without every pull request touching a shared file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from .text import slugify

DEFAULT_ACCENT = "#6366f1"

#: Bios whose ``team`` cannot be resolved are grouped here instead of dropped.
FALLBACK_TEAM_NAME = "Unassigned"
FALLBACK_ACCENT = "#8b95a8"


class ConfigError(Exception):
    """Raised when ``site.yml`` is missing or malformed."""


@dataclass(frozen=True, slots=True)
class Team:
    name: str
    tagline: str = ""
    accent: str = DEFAULT_ACCENT

    @property
    def slug(self) -> str:
        return slugify(self.name)


@dataclass(frozen=True, slots=True)
class SiteConfig:
    title: str
    tagline: str
    course: str
    footer: str
    teams: tuple[Team, ...]

    @classmethod
    def load(cls, path: Path) -> SiteConfig:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except FileNotFoundError as exc:
            raise ConfigError(f"{path}: not found") from exc
        except yaml.YAMLError as exc:
            raise ConfigError(f"{path}: invalid YAML - {exc}") from exc
        if not isinstance(raw, dict):
            raise ConfigError(f"{path}: expected a YAML mapping at the top level")

        teams_raw = raw.get("teams") or []
        if not isinstance(teams_raw, list) or not teams_raw:
            raise ConfigError(f"{path}: 'teams' must be a non-empty list")

        teams: list[Team] = []
        for entry in teams_raw:
            if isinstance(entry, str):
                teams.append(Team(name=entry.strip()))
                continue
            if not isinstance(entry, dict) or not entry.get("name"):
                raise ConfigError(f"{path}: every team needs a 'name'")
            teams.append(
                Team(
                    name=str(entry["name"]).strip(),
                    tagline=str(entry.get("tagline", "")).strip(),
                    accent=str(entry.get("accent", DEFAULT_ACCENT)).strip(),
                )
            )

        return cls(
            title=str(raw.get("title", "Student Bios")).strip(),
            tagline=str(raw.get("tagline", "")).strip(),
            course=str(raw.get("course", "")).strip(),
            footer=str(raw.get("footer", "")).strip(),
            teams=tuple(teams),
        )

    def team(self, name: str) -> Team | None:
        """Look up a team by name, ignoring case and surrounding whitespace."""
        wanted = name.strip().casefold()
        for team in self.teams:
            if team.name.casefold() == wanted:
                return team
        return None

    @property
    def fallback_team(self) -> Team:
        """The bucket for bios whose ``team`` could not be resolved.

        Synthetic rather than configured: an instructor should not have to
        remember to add it, and a bio landing here is a defect to fix, not a
        team to plan around. It renders after the real teams.
        """
        return Team(
            name=FALLBACK_TEAM_NAME,
            tagline="Team field missing or misspelled - fix the 'team' value in the bio file",
            accent=FALLBACK_ACCENT,
        )

    @property
    def team_names(self) -> tuple[str, ...]:
        return tuple(team.name for team in self.teams)
