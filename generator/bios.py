"""Parsing and validation for one YAML bio file per student.

A bio file is a YAML mapping. Everything is structured data except ``about``,
which is a block scalar holding a few sentences of Markdown:

    name: Jane Doe
    team: Team Falcon
    headline: Backend engineer who likes boring infrastructure
    about: |
      Two or three sentences about Jane. This is **Markdown**, so bold,
      links and lists all work.

YAML is unforgiving about three things in particular - tab indentation, an
unquoted ``": "`` inside a value, and the indentation of a block scalar - so
each of those gets its own message here rather than leaking PyYAML's wording.
Every rule is reported as a :class:`Problem` naming the file it came from, so a
red CI check reads like instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import markdown
import yaml
from markupsafe import Markup

from .config import SiteConfig
from .text import hue_for, initials, slugify

FILENAME = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)+\.yml\Z")
UNSAFE_HTML = re.compile(r"<\s*(?:script|iframe|object|embed)\b|javascript:", re.IGNORECASE)
LEADING_TAB = re.compile(r"^[ ]*\t", re.MULTILINE)

#: Files in ``bios/`` that are documentation, not student bios.
RESERVED_FILES = frozenset({"TEMPLATE.yml"})

REQUIRED_KEYS = ("name", "team", "headline", "about")
ALLOWED_KEYS = frozenset(
    {
        "name",
        "team",
        "headline",
        "about",
        "pronouns",
        "location",
        "focus",
        "links",
        "avatar",
        "fun_fact",
    }
)

HEADLINE_MAX = 90
ABOUT_MIN = 40
ABOUT_MAX = 2000
FOCUS_MAX = 6
FOCUS_ITEM_MAX = 24

MARKDOWN_EXTENSIONS = ("extra", "sane_lists", "smarty")

_ABOUT_SHAPE = "about: |\n  Two or three sentences about you."


@dataclass(frozen=True, slots=True)
class Problem:
    """One actionable validation failure, tied to the file that caused it."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass(frozen=True, slots=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class Bio:
    slug: str
    name: str
    team: str
    headline: str
    body_html: Markup
    source: str
    pronouns: str | None = None
    location: str | None = None
    fun_fact: str | None = None
    avatar: str | None = None
    focus: tuple[str, ...] = ()
    links: tuple[Link, ...] = ()

    @property
    def url(self) -> str:
        return f"/{self.slug}/"

    @property
    def initials(self) -> str:
        return initials(self.name)

    @property
    def hue(self) -> int:
        return hue_for(self.slug)

    @property
    def sort_key(self) -> tuple[str, str]:
        """Sort by family name, falling back to the slug for stability."""
        parts = self.name.split()
        family = slugify(parts[-1]) if parts else self.slug
        return (family, self.slug)


def _as_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool) or isinstance(value, (dict, list)):
        return None
    return str(value).strip()


def _yaml_message(exc: yaml.YAMLError) -> str:
    """Turn a PyYAML error into something a first-time YAML author can act on."""
    problem = getattr(exc, "problem", None) or "could not be parsed"
    mark = getattr(exc, "problem_mark", None)
    where = f"line {mark.line + 1}" if mark is not None else "somewhere in the file"
    hint = ""
    if "mapping values are not allowed" in problem:
        hint = " - a value containing ': ' must be wrapped in quotes"
    elif "could not find expected ':'" in problem:
        hint = " - every field is 'key: value', and continuation lines must be indented"
    elif "found character '\\t'" in problem:
        hint = " - YAML does not allow tabs; indent with spaces"
    elif "another document" in problem or "expected a single document" in problem:
        hint = " - remove the '---' lines; the whole file is YAML, not Markdown with front matter"
    return f"invalid YAML at {where}: {problem}{hint}"


def parse_bio(path: Path, config: SiteConfig, *, display_path: str | None = None) -> tuple[Bio | None, list[Problem]]:
    """Parse and validate a single bio file.

    Returns ``(bio, problems)``. ``bio`` is ``None`` when the file could not be
    turned into a valid record; ``problems`` is empty only for a valid file.
    """
    rel = display_path or path.as_posix()
    problems: list[Problem] = []

    def fail(message: str) -> tuple[None, list[Problem]]:
        problems.append(Problem(rel, message))
        return None, problems

    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return fail("file is not valid UTF-8 text - re-save it as UTF-8")
    except OSError as exc:
        return fail(f"could not read file - {exc}")

    if not FILENAME.match(path.name):
        return fail(
            "filename must be lowercase 'firstname-lastname.yml' "
            "(letters, digits and hyphens only)"
        )

    if LEADING_TAB.search(text):
        return fail("indented with a tab - YAML only allows spaces, so replace tabs with two spaces")

    try:
        data = yaml.safe_load(text.lstrip("\ufeff"))
    except yaml.YAMLError as exc:
        return fail(_yaml_message(exc))

    if data is None:
        return fail("file is empty - start from bios/TEMPLATE.yml")
    if not isinstance(data, dict):
        return fail("file must be a list of 'key: value' fields - start from bios/TEMPLATE.yml")

    for key in sorted(set(data) - ALLOWED_KEYS):
        problems.append(
            Problem(rel, f"unknown key {key!r} - allowed keys are: {', '.join(sorted(ALLOWED_KEYS))}")
        )

    if isinstance(data.get("about"), (dict, list)):
        return fail(f"'about' must be a block of text, written as:\n{_ABOUT_SHAPE}")

    missing = [key for key in REQUIRED_KEYS if not _as_text(data.get(key))]
    if missing:
        for key in missing:
            hint = f", written as:\n{_ABOUT_SHAPE}" if key == "about" else ""
            problems.append(Problem(rel, f"missing required key {key!r}{hint}"))
        return None, problems

    name = _as_text(data["name"]) or ""
    team_name = _as_text(data["team"]) or ""
    headline = _as_text(data["headline"]) or ""
    about = str(data["about"]).strip()

    expected_filename = f"{slugify(name)}.yml"
    if path.name != expected_filename:
        problems.append(
            Problem(rel, f"filename must be {expected_filename!r} to match name {name!r}")
        )

    team = config.team(team_name)
    if team is None:
        problems.append(
            Problem(
                rel,
                f"team {team_name!r} is not one of the course teams - use one of: "
                f"{', '.join(config.team_names)}",
            )
        )

    if len(headline) > HEADLINE_MAX:
        problems.append(
            Problem(rel, f"headline is {len(headline)} characters - keep it under {HEADLINE_MAX}")
        )

    focus_raw = data.get("focus") or []
    focus: list[str] = []
    if isinstance(focus_raw, str):
        problems.append(Problem(rel, "'focus' must be a YAML list, e.g. '- Python'"))
    elif isinstance(focus_raw, list):
        for item in focus_raw:
            value = _as_text(item)
            if not value:
                problems.append(Problem(rel, "'focus' entries must be short strings"))
                continue
            if len(value) > FOCUS_ITEM_MAX:
                problems.append(
                    Problem(rel, f"focus entry {value!r} is too long - keep each under {FOCUS_ITEM_MAX} characters")
                )
                continue
            focus.append(value)
        if len(focus) > FOCUS_MAX:
            problems.append(Problem(rel, f"'focus' has {len(focus)} entries - keep at most {FOCUS_MAX}"))
            focus = focus[:FOCUS_MAX]
    else:
        problems.append(Problem(rel, "'focus' must be a YAML list of short strings"))

    links_raw = data.get("links") or {}
    links: list[Link] = []
    if isinstance(links_raw, dict):
        for label, url in links_raw.items():
            label_text = _as_text(label)
            url_text = _as_text(url)
            if not label_text or not url_text:
                problems.append(Problem(rel, "each link needs a label and a URL"))
                continue
            if not url_text.startswith(("http://", "https://", "mailto:")):
                problems.append(
                    Problem(rel, f"link {label_text!r} must start with 'https://' (got {url_text!r})")
                )
                continue
            links.append(Link(label=label_text, url=url_text))
    else:
        problems.append(
            Problem(rel, "'links' must be a mapping of label to URL, e.g. 'GitHub: https://github.com/you'")
        )

    avatar = _as_text(data.get("avatar"))
    if avatar and not avatar.startswith(("http://", "https://")):
        problems.append(Problem(rel, "'avatar' must be an https URL, or leave it out for a monogram"))
        avatar = None

    body_html = Markup(markdown.markdown(about, extensions=list(MARKDOWN_EXTENSIONS)))

    if UNSAFE_HTML.search(about):
        problems.append(Problem(rel, "remove embedded HTML/JavaScript - 'about' is Markdown only"))
    elif len(about) < ABOUT_MIN:
        problems.append(
            Problem(rel, f"'about' is {len(about)} characters - write at least {ABOUT_MIN} (a sentence or two)")
        )
    elif len(about) > ABOUT_MAX:
        problems.append(
            Problem(rel, f"'about' is {len(about)} characters - trim it to under {ABOUT_MAX}")
        )
    elif "<pre" in body_html:
        problems.append(
            Problem(
                rel,
                "part of 'about' renders as a code block instead of prose - indent every line "
                "exactly two spaces under 'about: |' and drop any ``` fences",
            )
        )

    if problems:
        return None, problems

    bio = Bio(
        slug=path.stem,
        name=name,
        team=team.name if team else team_name,
        headline=headline,
        body_html=body_html,
        source=rel,
        pronouns=_as_text(data.get("pronouns")),
        location=_as_text(data.get("location")),
        fun_fact=_as_text(data.get("fun_fact")),
        avatar=avatar,
        focus=tuple(focus),
        links=tuple(links),
    )
    return bio, []


def load_bios(bios_dir: Path, config: SiteConfig) -> tuple[tuple[Bio, ...], tuple[Problem, ...]]:
    """Load every ``bios/*.yml`` file: whatever is present makes up the site."""
    problems: list[Problem] = []
    if not bios_dir.is_dir():
        return (), (Problem(bios_dir.as_posix(), "bios directory not found"),)

    bios: list[Bio] = []
    for path in sorted(bios_dir.glob("*.y*ml")):
        if path.name in RESERVED_FILES:
            continue
        bio, file_problems = parse_bio(path, config, display_path=path.as_posix())
        problems.extend(file_problems)
        if bio is not None:
            bios.append(bio)

    bios.sort(key=lambda item: item.sort_key)
    return tuple(bios), tuple(problems)
