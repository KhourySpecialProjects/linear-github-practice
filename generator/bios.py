"""Parsing and validation for one Markdown bio file per student.

A bio file is YAML frontmatter plus a Markdown body:

    ---
    name: Jane Doe
    team: Team Falcon
    headline: Backend engineer who likes boring infrastructure
    ---

    Two or three sentences about Jane.

Every rule enforced here is reported as a :class:`Problem` with the file it
came from, so CI failures read like instructions rather than tracebacks.
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

FRONTMATTER = re.compile(
    r"\A---[ \t]*\r?\n(?P<meta>.*?)\r?\n---[ \t]*\r?\n?(?P<body>.*)\Z",
    re.DOTALL,
)
FILENAME = re.compile(r"\A[a-z0-9]+(?:-[a-z0-9]+)+\.md\Z")
UNSAFE_HTML = re.compile(r"<\s*(?:script|iframe|object|embed)\b|javascript:", re.IGNORECASE)

#: Files in ``bios/`` that are documentation, not student bios.
RESERVED_FILES = frozenset({"TEMPLATE.md", "README.md"})

REQUIRED_KEYS = ("name", "team", "headline")
ALLOWED_KEYS = frozenset(
    {
        "name",
        "team",
        "headline",
        "pronouns",
        "location",
        "focus",
        "links",
        "avatar",
        "fun_fact",
    }
)

HEADLINE_MAX = 90
BODY_MIN = 40
BODY_MAX = 2000
FOCUS_MAX = 6
FOCUS_ITEM_MAX = 24

MARKDOWN_EXTENSIONS = ("extra", "sane_lists", "smarty")


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
            "filename must be lowercase 'firstname-lastname.md' "
            "(letters, digits and hyphens only)"
        )

    match = FRONTMATTER.match(text.lstrip("\ufeff"))
    if not match:
        return fail(
            "no frontmatter found - the file must start with '---' on line 1, "
            "then the YAML fields, then a closing '---'"
        )

    try:
        meta = yaml.safe_load(match.group("meta")) or {}
    except yaml.YAMLError as exc:
        first_line = str(exc).splitlines()[0]
        return fail(f"frontmatter is not valid YAML - {first_line}")
    if not isinstance(meta, dict):
        return fail("frontmatter must be a list of 'key: value' fields")

    for key in sorted(set(meta) - ALLOWED_KEYS):
        problems.append(
            Problem(rel, f"unknown frontmatter key {key!r} - allowed keys are: {', '.join(sorted(ALLOWED_KEYS))}")
        )

    missing = [key for key in REQUIRED_KEYS if not _as_text(meta.get(key))]
    if missing:
        for key in missing:
            problems.append(Problem(rel, f"missing required frontmatter key {key!r}"))
        return None, problems

    name = _as_text(meta["name"]) or ""
    team_name = _as_text(meta["team"]) or ""
    headline = _as_text(meta["headline"]) or ""

    expected_filename = f"{slugify(name)}.md"
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

    focus_raw = meta.get("focus") or []
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

    links_raw = meta.get("links") or {}
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

    avatar = _as_text(meta.get("avatar"))
    if avatar and not avatar.startswith(("http://", "https://")):
        problems.append(Problem(rel, "'avatar' must be an https URL, or leave it out for a monogram"))
        avatar = None

    body = match.group("body").strip()
    if UNSAFE_HTML.search(body):
        problems.append(Problem(rel, "remove embedded HTML/JavaScript - the bio body is Markdown only"))
    elif len(body) < BODY_MIN:
        problems.append(
            Problem(rel, f"bio body is {len(body)} characters - write at least {BODY_MIN} (a sentence or two)")
        )
    elif len(body) > BODY_MAX:
        problems.append(
            Problem(rel, f"bio body is {len(body)} characters - trim it to under {BODY_MAX}")
        )

    if problems:
        return None, problems

    body_html = Markup(markdown.markdown(body, extensions=list(MARKDOWN_EXTENSIONS)))
    bio = Bio(
        slug=path.stem,
        name=name,
        team=team.name if team else team_name,
        headline=headline,
        body_html=body_html,
        source=rel,
        pronouns=_as_text(meta.get("pronouns")),
        location=_as_text(meta.get("location")),
        fun_fact=_as_text(meta.get("fun_fact")),
        avatar=avatar,
        focus=tuple(focus),
        links=tuple(links),
    )
    return bio, []


def load_bios(bios_dir: Path, config: SiteConfig) -> tuple[tuple[Bio, ...], tuple[Problem, ...]]:
    """Load every ``bios/*.md`` file: whatever is present makes up the site."""
    problems: list[Problem] = []
    if not bios_dir.is_dir():
        return (), (Problem(bios_dir.as_posix(), "bios directory not found"),)

    bios: list[Bio] = []
    for path in sorted(bios_dir.glob("*.md")):
        if path.name in RESERVED_FILES:
            continue
        bio, file_problems = parse_bio(path, config, display_path=path.as_posix())
        problems.extend(file_problems)
        if bio is not None:
            bios.append(bio)

    bios.sort(key=lambda item: item.sort_key)
    return tuple(bios), tuple(problems)
