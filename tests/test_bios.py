"""Tests for the validator contract that gates every student pull request.

The exercise lives or dies on `python -m generator validate` telling a student
exactly what to fix, so these tests assert on the *problems* a bad bio file
produces (by substring, so wording can be improved without breaking the suite)
and on the values a template is allowed to read off a good one.

Parsing is now strict where it teaches and resilient where it deploys: a bad
file always still yields a renderable :class:`Bio` built from fallback values,
`validate` fails on the reported problems, and `build` warns and ships the
degraded card unless it is asked for `--strict`. So every test about a broken
file asserts two things - the message a student reads, and the fallback a
visitor sees.

A bio is a plain YAML mapping, so YAML's own sharp edges - tabs, an unquoted
``": "`` inside a value, an empty file, a block scalar written as a nested
mapping - are part of the contract and get their own tests.
"""

from __future__ import annotations

import re
import textwrap
from html import unescape
from pathlib import Path

import pytest

from generator.__main__ import main
from generator.bios import (
    ABOUT_MAX,
    ABOUT_MIN,
    FALLBACK_HEADLINE,
    FALLBACK_NAME,
    FOCUS_ITEM_MAX,
    FOCUS_MAX,
    HEADLINE_MAX,
    Link,
    load_bios,
    name_from_filename,
    parse_bio,
)
from generator.config import (
    FALLBACK_ACCENT,
    FALLBACK_TEAM_NAME,
    ConfigError,
    SiteConfig,
)
from generator.render import BuildError, build, group_by_team
from generator.text import hue_for, initials, slugify

SITE_YML = """\
title: Practicum Bios
tagline: One file per teammate
course: Khoury Practicum
footer: Northeastern University
teams:
  - name: Team Falcon
    tagline: Fast feedback
    accent: "#7c5cff"
  - name: Team Kestrel
    tagline: Calm releases
    accent: "#00b6a4"
"""

#: The roster the course actually runs, for the tests where the *number* of
#: teams matters. Teams are data: the code never hardcodes how many there are.
ELEVEN_TEAMS = (
    ("Team Falcon", "#7c5cff"),
    ("Team Kestrel", "#00b6a4"),
    ("Team Osprey", "#ff7a45"),
    ("Team Harrier", "#3b82f6"),
    ("Team Merlin", "#ec4899"),
    ("Team Goshawk", "#22c55e"),
    ("Team Kite", "#f59e0b"),
    ("Team Caracara", "#8b5cf6"),
    ("Team Peregrine", "#06b6d4"),
    ("Team Condor", "#ef4444"),
    ("Team Eagle", "#14b8a6"),
)

ELEVEN_TEAM_NAMES = tuple(name for name, _ in ELEVEN_TEAMS)

ELEVEN_TEAM_YML = "title: Practicum Bios\ntagline: Eleven teams\nteams:\n" + "".join(
    f'  - name: {name}\n    tagline: Ships things\n    accent: "{accent}"\n'
    for name, accent in ELEVEN_TEAMS
)

#: The Markdown that lives in the ``about:`` block scalar of a good bio.
ABOUT = """\
I work on **APIs** and the boring infrastructure underneath them.

- Comfortable in Python and Go
- Learning Kubernetes the hard way
"""

#: A one-line ``about:`` block, for tests that assemble the document by hand.
ONE_LINE_ABOUT = "about: |\n  A sentence about Jane that clears the minimum length comfortably.\n"

REQUIRED_FIELDS = {
    "name": "name: Jane Doe",
    "team": "team: Team Falcon",
    "headline": "headline: Backend engineer who likes boring infrastructure",
}

MINIMAL = "\n".join(REQUIRED_FIELDS.values())

#: For each required key left out of ``jane-doe.yml``: the field that gets
#: substituted, and the value a visitor ends up reading on the card.
FALLBACK_FOR_MISSING = {
    "name": ("name", "Jane Doe"),  # derived from the filename, not a placeholder
    "team": ("team", FALLBACK_TEAM_NAME),
    "headline": ("headline", FALLBACK_HEADLINE),
}


@pytest.fixture
def config_path(tmp_path):
    path = tmp_path / "site.yml"
    path.write_text(SITE_YML, encoding="utf-8")
    return path


@pytest.fixture
def config(config_path):
    """A real SiteConfig, loaded from YAML, so the loader is exercised too."""
    return SiteConfig.load(config_path)


@pytest.fixture
def eleven_team_config(tmp_path):
    """The full roster, for grouping and team-count behaviour."""
    path = tmp_path / "site-eleven.yml"
    path.write_text(ELEVEN_TEAM_YML, encoding="utf-8")
    return SiteConfig.load(path)


@pytest.fixture
def bios_dir(tmp_path):
    directory = tmp_path / "bios"
    directory.mkdir()
    return directory


def write_bio(directory, filename: str, fields: str = MINIMAL, about: str | None = ABOUT):
    """Write one YAML bio the way a student would, and return its path.

    ``fields`` is the structured part of the mapping; ``about`` is appended as
    a block scalar unless it is ``None`` (for the tests that write their own
    ``about``, or deliberately leave it out).
    """
    path = directory / filename
    document = textwrap.dedent(fields).strip("\n")
    if about is not None:
        block = textwrap.indent(textwrap.dedent(about).strip("\n"), "  ")
        document = f"{document}\nabout: |\n{block}"
    path.write_text(f"{document}\n", encoding="utf-8")
    return path


def messages(problems) -> str:
    """All problem messages joined, for substring assertions."""
    return "\n".join(problem.message for problem in problems)


def prose(body_html) -> str:
    """The words a visitor reads, with the Markdown-rendered tags taken back off."""
    return unescape(re.sub(r"<[^>]+>", " ", str(body_html))).strip()


def test_valid_bio_exposes_the_values_templates_read(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        """
        name: Jane Doe
        team: team falcon
        headline: Backend engineer who likes boring infrastructure
        pronouns: she/her
        location: Boston, MA
        avatar: https://example.com/jane.png
        fun_fact: Keeps a sourdough starter named after a database.
        focus:
          - Python
          - Postgres
        links:
          GitHub: https://github.com/janedoe
          Email: mailto:doe.j@northeastern.edu
        """,
    )

    bio, problems = parse_bio(path, config)

    assert problems == []
    # Nothing had to be repaired, so the card is the student's own words.
    assert bio.salvaged is False
    assert bio.name == "Jane Doe"
    # The team name is canonicalised to site.yml's spelling, not the student's.
    assert bio.team == "Team Falcon"
    assert bio.slug == "jane-doe"
    assert bio.url == "/jane-doe/"
    assert bio.headline == "Backend engineer who likes boring infrastructure"
    assert bio.pronouns == "she/her"
    assert bio.location == "Boston, MA"
    assert bio.avatar == "https://example.com/jane.png"
    assert bio.fun_fact.startswith("Keeps a sourdough starter")
    assert bio.focus == ("Python", "Postgres")
    assert bio.links == (
        Link(label="GitHub", url="https://github.com/janedoe"),
        Link(label="Email", url="mailto:doe.j@northeastern.edu"),
    )
    assert bio.initials == "JD"
    # 'about' is a block scalar but it is still rendered as Markdown.
    assert "<strong>APIs</strong>" in bio.body_html
    assert "<li>Comfortable in Python and Go</li>" in bio.body_html


@pytest.mark.parametrize("missing", sorted(REQUIRED_FIELDS))
def test_each_missing_required_key_names_the_key_and_substitutes_a_fallback(bios_dir, config, missing):
    fields = "\n".join(line for key, line in REQUIRED_FIELDS.items() if key != missing)
    path = write_bio(bios_dir, "jane-doe.yml", fields)

    bio, problems = parse_bio(path, config)

    assert f"missing required key '{missing}'" in messages(problems)
    field, fallback = FALLBACK_FOR_MISSING[missing]
    assert getattr(bio, field) == fallback
    assert bio.salvaged is True


def test_missing_about_shows_the_block_scalar_shape_and_renders_the_placeholder(bios_dir, config):
    path = write_bio(bios_dir, "jane-doe.yml", MINIMAL, about=None)

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "missing required key 'about'" in text
    # The student is shown the shape, because 'about: |' is the part they get wrong.
    assert "about: |" in text
    assert "Two or three sentences" in text
    # The card still renders, and says out loud that the bio could not be read.
    body = prose(bio.body_html)
    assert "could not be read" in body
    assert "generator validate" in body
    assert bio.salvaged is True


def test_unknown_key_is_reported_but_the_rest_of_the_bio_still_renders(bios_dir, config):
    path = write_bio(bios_dir, "jane-doe.yml", f"{MINIMAL}\ntwitter: '@janedoe'")

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "unknown key 'twitter'" in text
    # The allowed-key list is spelled out rather than hinted at.
    assert "fun_fact" in text
    assert "pronouns" in text
    # An unknown key is ignored, not fatal: every real field survives.
    assert (bio.name, bio.team, bio.headline) == (
        "Jane Doe",
        "Team Falcon",
        "Backend engineer who likes boring infrastructure",
    )
    assert bio.salvaged is True


def test_unknown_team_lands_in_unassigned_and_lists_the_course_teams(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        """
        name: Jane Doe
        team: Team Penguin
        headline: Backend engineer who likes boring infrastructure
        """,
    )

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "Team Penguin" in text
    assert "Team Falcon" in text
    assert "Team Kestrel" in text
    # The bio is bucketed, not dropped: the card is still reachable.
    assert bio.team == FALLBACK_TEAM_NAME
    assert bio.name == "Jane Doe"
    assert bio.salvaged is True


def test_filename_must_match_the_name_field(bios_dir, config):
    wrong = write_bio(bios_dir, "jane-doe.yml", "name: Jane Zebra\n" + "\n".join(
        line for key, line in REQUIRED_FIELDS.items() if key != "name"
    ))

    bio, problems = parse_bio(wrong, config)

    text = messages(problems)
    assert "jane-zebra.yml" in text
    assert "Jane Zebra" in text
    # The name the student wrote is kept; only the page address comes from the file.
    assert bio.name == "Jane Zebra"
    assert bio.slug == "jane-doe"
    assert bio.salvaged is True

    # Control: the identical bio under the matching filename is accepted, so
    # this test cannot pass just because something else is broken.
    right = write_bio(bios_dir, "jane-zebra.yml", "name: Jane Zebra\n" + "\n".join(
        line for key, line in REQUIRED_FIELDS.items() if key != "name"
    ))
    good, no_problems = parse_bio(right, config)
    assert no_problems == []
    assert good.slug == "jane-zebra"
    assert good.salvaged is False


@pytest.mark.parametrize(
    "filename",
    [
        "Jane-Doe.yml",  # uppercase
        "jane doe.yml",  # space
        "jane_doe.yml",  # underscore
        "jane.yml",  # no hyphen, so no family name
        "jane-doe.yaml",  # the wrong extension is reported, not ignored
    ],
)
def test_bad_filenames_are_reported_and_the_bio_still_renders(bios_dir, config, filename):
    path = write_bio(bios_dir, filename)

    bio, problems = parse_bio(path, config)

    assert "filename must be lowercase" in messages(problems)
    assert bio.name == "Jane Doe"
    assert bio.team == "Team Falcon"
    assert bio.salvaged is True


def test_yaml_extension_is_reported_by_the_loader_not_silently_skipped(bios_dir, config):
    # load_bios globs '*.y*ml' precisely so a student who saves '.yaml' gets a
    # filename error instead of a mysteriously missing bio page.
    write_bio(bios_dir, "jane-doe.yaml")

    bios, problems = load_bios(bios_dir, config)

    assert [bio.slug for bio in bios] == ["jane-doe"]
    assert {problem.path.rsplit("/", 1)[-1] for problem in problems} == {"jane-doe.yaml"}
    assert "filename must be lowercase" in messages(problems)


def test_about_shorter_than_the_minimum_is_reported_but_kept_verbatim(bios_dir, config):
    path = write_bio(bios_dir, "jane-doe.yml", about="Too short.")

    bio, problems = parse_bio(path, config)

    assert f"at least {ABOUT_MIN}" in messages(problems)
    # A thin bio is the student's own words, so it is published as written -
    # replacing it with the placeholder would lose content, not repair it.
    assert prose(bio.body_html) == "Too short."
    assert "could not be read" not in prose(bio.body_html)
    assert bio.salvaged is True


def test_about_of_exactly_the_minimum_length_is_valid(bios_dir, config):
    exact = "Exactly forty characters of honest prose"
    assert len(exact) == ABOUT_MIN

    path = write_bio(bios_dir, "jane-doe.yml", about=exact)

    bio, problems = parse_bio(path, config)

    assert problems == []
    assert bio.salvaged is False
    assert prose(bio.body_html) == exact


def test_about_longer_than_the_maximum_is_truncated_on_a_word_boundary(bios_dir, config):
    original = ("Detail about the honest work of shipping software " * 45).strip()
    assert len(original) > ABOUT_MAX
    path = write_bio(bios_dir, "jane-doe.yml", about=original)

    bio, problems = parse_bio(path, config)

    assert f"under {ABOUT_MAX}" in messages(problems)
    published = prose(bio.body_html)
    assert len(published) <= ABOUT_MAX
    assert published.endswith("\u2026")
    stem = published[:-1]
    # The cut lands between words: the kept text is a prefix of the original
    # and the character it stopped before is a space, not a letter.
    assert original.startswith(stem)
    assert original[len(stem)] == " "
    assert bio.salvaged is True


def test_headline_longer_than_the_maximum_is_truncated_on_a_word_boundary(bios_dir, config):
    original = "Backend engineer who likes boring infrastructure and honest deployment runbooks for everybody"
    assert len(original) > HEADLINE_MAX
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"name: Jane Doe\nteam: Team Falcon\nheadline: {original}",
    )

    bio, problems = parse_bio(path, config)

    assert f"under {HEADLINE_MAX}" in messages(problems)
    assert len(bio.headline) <= HEADLINE_MAX
    assert bio.headline.endswith("\u2026")
    stem = bio.headline[:-1]
    assert original.startswith(stem)
    assert original[len(stem)] == " "
    assert bio.salvaged is True


def test_too_many_focus_entries_keep_the_first_six(bios_dir, config):
    # Eight entries is a literal over-run of the documented limit of six: if the
    # cap were quietly raised, this bio would be accepted and the test would fail.
    entries = "\n".join(f"  - Skill {index}" for index in range(8))
    path = write_bio(bios_dir, "jane-doe.yml", f"{MINIMAL}\nfocus:\n{entries}")

    bio, problems = parse_bio(path, config)

    assert f"at most {FOCUS_MAX}" in messages(problems)
    assert bio.focus == tuple(f"Skill {index}" for index in range(FOCUS_MAX))
    assert bio.salvaged is True


def test_focus_entry_longer_than_a_chip_is_dropped_and_its_siblings_survive(bios_dir, config):
    # 'focus' renders as small chips, so a sentence smuggled into one is a
    # layout bug: 31 characters is a literal over-run of the 24-character rule.
    long_entry = "Distributed systems and caching"
    assert len(long_entry) > FOCUS_ITEM_MAX
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"{MINIMAL}\nfocus:\n  - Python\n  - {long_entry}\n  - Postgres",
    )

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert long_entry in text
    assert f"under {FOCUS_ITEM_MAX} characters" in text
    assert bio.focus == ("Python", "Postgres")
    assert bio.salvaged is True


def test_link_without_a_scheme_is_dropped_and_the_good_link_survives(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"{MINIMAL}\nlinks:\n  GitHub: github.com/janedoe\n  Email: mailto:doe.j@northeastern.edu",
    )

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "GitHub" in text
    assert "https://" in text
    assert bio.links == (Link(label="Email", url="mailto:doe.j@northeastern.edu"),)
    assert bio.salvaged is True


def test_avatar_that_is_not_a_url_is_dropped_and_the_rest_of_the_card_survives(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"{MINIMAL}\navatar: images/jane.png\nfocus:\n  - Python\n"
        "links:\n  GitHub: https://github.com/janedoe",
    )

    bio, problems = parse_bio(path, config)

    assert "'avatar' must be an https URL" in messages(problems)
    # Dropping the avatar falls back to the monogram; nothing else is lost.
    assert bio.avatar is None
    assert bio.initials == "JD"
    assert bio.focus == ("Python",)
    assert bio.links == (Link(label="GitHub", url="https://github.com/janedoe"),)
    assert bio.salvaged is True


def test_raw_script_in_about_is_stripped_and_the_prose_survives(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        about="Backend engineer. <script>alert('hi')</script> And some more prose here.",
    )

    bio, problems = parse_bio(path, config)

    assert "HTML/JavaScript" in messages(problems)
    rendered = str(bio.body_html)
    assert "<script" not in rendered
    assert "</script" not in rendered
    assert "javascript:" not in rendered
    body = prose(bio.body_html)
    assert "Backend engineer." in body
    assert "And some more prose here." in body
    assert bio.salvaged is True


def test_tab_indentation_is_reported_in_terms_of_tabs_and_spaces(bios_dir, config):
    path = bios_dir / "jane-doe.yml"
    path.write_text(f"{MINIMAL}\nfocus:\n\t- Python\nabout: |\n  {ABOUT.strip()}\n", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    # Tabs get their own instruction, first, instead of the student having to
    # decode PyYAML's wording, which points at a column rather than telling
    # them what to type.
    assert "replace tabs with two spaces" in problems[0].message
    # The file cannot be parsed at all, so the card is built entirely from fallbacks.
    assert (bio.name, bio.team, bio.headline) == ("Jane Doe", FALLBACK_TEAM_NAME, FALLBACK_HEADLINE)
    assert bio.salvaged is True


def test_unquoted_colon_in_a_value_is_reported_with_a_quoting_hint(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        """
        name: Jane Doe
        team: Team Falcon
        headline: Backend engineer: likes boring infra
        """,
    )

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "invalid YAML at line" in text
    assert "quotes" in text
    assert bio.headline == FALLBACK_HEADLINE
    assert bio.salvaged is True


@pytest.mark.parametrize(
    ("label", "content"),
    [
        ("unparseable YAML", b"name: Jane Doe\nteam Team Falcon\n"),
        ("empty file", b""),
        ("whitespace only", b"\n  \n"),
        ("top-level list", b"- name: Jane Doe\n- team: Team Falcon\n"),
        ("bare scalar", b"just some prose about Jane\n"),
        ("not UTF-8", b"name: Jos\xe9 Doe\n"),
    ],
)
def test_a_file_that_cannot_be_read_still_renders_from_fallbacks(bios_dir, config, label, content):
    """The deployed site must survive a file that is broken beyond repair.

    Every field falls back, the card renders, and `validate` still has a
    problem to fail on - which is the whole strict/lenient split.
    """
    path = bios_dir / "jane-doe.yml"
    path.write_bytes(content)

    bio, problems = parse_bio(path, config)

    assert problems, label
    assert bio.salvaged is True
    assert bio.slug == "jane-doe"
    assert bio.name == "Jane Doe"  # from the filename, so the card is not anonymous
    assert bio.team == FALLBACK_TEAM_NAME
    assert bio.headline == FALLBACK_HEADLINE
    assert "could not be read" in prose(bio.body_html)
    assert bio.focus == ()
    assert bio.links == ()
    assert bio.avatar is None


def test_empty_file_points_at_the_template(bios_dir, config):
    path = bios_dir / "jane-doe.yml"
    path.write_text("", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "empty" in text
    assert "TEMPLATE.yml" in text
    assert bio.headline == FALLBACK_HEADLINE


@pytest.mark.parametrize(
    "document",
    [
        "- name: Jane Doe\n- team: Team Falcon\n",  # a top-level list
        "just some prose about Jane\n",  # a bare scalar
    ],
)
def test_top_level_must_be_a_mapping_of_fields(bios_dir, config, document):
    path = bios_dir / "jane-doe.yml"
    path.write_text(document, encoding="utf-8")

    bio, problems = parse_bio(path, config)

    assert "'key: value' fields" in messages(problems)
    assert bio.team == FALLBACK_TEAM_NAME


def test_name_from_filename_reads_a_display_name_off_the_path():
    assert name_from_filename(Path("bios/jane-doe.yml")) == "Jane Doe"
    assert name_from_filename(Path("bios/ada-b-lovelace.yml")) == "Ada B Lovelace"
    assert name_from_filename(Path("bios/jose-alvarez.yml")) == "Jose Alvarez"
    # Only when the filename yields nothing usable does the placeholder appear.
    assert name_from_filename(Path("bios/---.yml")) == FALLBACK_NAME
    assert name_from_filename(Path("bios/_.yml")) == FALLBACK_NAME


def test_missing_name_is_derived_from_the_filename(bios_dir, config):
    path = write_bio(
        bios_dir,
        "ada-lovelace.yml",
        "team: Team Falcon\nheadline: Backend engineer who likes boring infrastructure",
    )

    bio, problems = parse_bio(path, config)

    assert "missing required key 'name'" in messages(problems)
    assert bio.name == "Ada Lovelace"
    assert bio.initials == "AL"
    assert bio.slug == "ada-lovelace"
    assert bio.salvaged is True


def test_name_that_is_not_text_is_derived_from_the_filename(bios_dir, config):
    path = write_bio(
        bios_dir,
        "ada-lovelace.yml",
        "name:\n  first: Ada\n  last: Lovelace\nteam: Team Falcon\nheadline: Backend engineer",
    )

    bio, problems = parse_bio(path, config)

    assert "'name' must be text" in messages(problems)
    assert bio.name == "Ada Lovelace"
    assert bio.salvaged is True


def test_over_indented_paragraph_is_flattened_instead_of_rendering_as_a_code_block(bios_dir, config):
    """Markdown turns a four-space indent into a code block, which looks broken.

    A student editing the template's ``about`` block is one stray Tab-to-spaces
    away from this, and the rendered page gives no clue why their sentence came
    out grey and monospaced.
    """
    path = bios_dir / "jane-doe.yml"
    path.write_text(
        f"{MINIMAL}\nabout: |\n  First paragraph, comfortably over the minimum length.\n\n"
        "      Second paragraph indented six spaces by accident.\n",
        encoding="utf-8",
    )

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "code block" in text
    assert "two spaces" in text
    # Reported *and* repaired: the paragraph is published as prose.
    assert "<pre" not in bio.body_html
    assert "Second paragraph indented six spaces by accident." in prose(bio.body_html)
    assert bio.salvaged is True


def test_a_fenced_code_block_in_about_is_flattened(bios_dir, config):
    path = bios_dir / "jane-doe.yml"
    path.write_text(
        f"{MINIMAL}\nabout: |\n  How I work, which is a long enough sentence to pass:\n\n"
        "  ```\n  git commit -m \"wip\"\n  ```\n",
        encoding="utf-8",
    )

    bio, problems = parse_bio(path, config)

    assert "code block" in messages(problems)
    assert "<pre" not in bio.body_html
    assert "How I work" in prose(bio.body_html)
    assert bio.salvaged is True


def test_a_leftover_front_matter_fence_is_explained(bios_dir, config):
    """Opening and closing '---' is two YAML documents, whose native error is opaque."""
    path = bios_dir / "jane-doe.yml"
    path.write_text(f"---\n{MINIMAL}\n{ONE_LINE_ABOUT}---\n", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "remove the '---' lines" in text
    assert bio.team == FALLBACK_TEAM_NAME
    assert bio.salvaged is True


def test_a_single_leading_document_marker_is_still_valid_yaml(bios_dir, config):
    """One '---' is legal YAML, so it must not be swept up by the fence check."""
    path = bios_dir / "jane-doe.yml"
    path.write_text(f"---\n{MINIMAL}\n{ONE_LINE_ABOUT}", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    assert problems == []
    assert bio.salvaged is False
    assert bio.team == "Team Falcon"


def test_about_written_as_a_nested_mapping_shows_the_block_scalar_shape(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"{MINIMAL}\nabout:\n  summary: I work on APIs and the infrastructure underneath them.",
        about=None,
    )

    bio, problems = parse_bio(path, config)

    text = messages(problems)
    assert "'about' must be a block of text" in text
    assert "about: |" in text
    assert "could not be read" in prose(bio.body_html)
    assert bio.salvaged is True


def test_load_bios_skips_the_template_and_ignores_the_readme(bios_dir, config):
    # TEMPLATE.yml is reserved, and README.md no longer even matches the glob.
    (bios_dir / "TEMPLATE.yml").write_text("name: Your Name\nteam: Your Team\n", encoding="utf-8")
    (bios_dir / "README.md").write_text("# How to add your bio\n", encoding="utf-8")
    write_bio(bios_dir, "jane-doe.yml")

    bios, problems = load_bios(bios_dir, config)

    assert problems == ()
    assert [bio.slug for bio in bios] == ["jane-doe"]


def test_load_bios_sorts_by_family_name(bios_dir, config):
    # Given names deliberately run A, B, J while family names run Z, A, M, so
    # the expected order cannot be produced by the directory glob alone.
    for filename, name in (
        ("ada-zebra.yml", "Ada Zebra"),
        ("bo-apple.yml", "Bo Apple"),
        ("jane-mango.yml", "Jane Mango"),
    ):
        write_bio(
            bios_dir,
            filename,
            f"name: {name}\nteam: Team Falcon\nheadline: Backend engineer",
        )

    bios, problems = load_bios(bios_dir, config)

    assert problems == ()
    assert [bio.name for bio in bios] == ["Bo Apple", "Jane Mango", "Ada Zebra"]


def test_load_bios_keeps_every_bad_file_and_reports_all_of_them(bios_dir, config):
    write_bio(bios_dir, "jane-doe.yml")
    write_bio(
        bios_dir,
        "bad-team.yml",
        "name: Bad Team\nteam: Team Penguin\nheadline: Backend engineer",
    )
    write_bio(bios_dir, "no-headline.yml", "name: No Headline\nteam: Team Falcon")
    (bios_dir / "broken-yaml.yml").write_text("name: Broken Yaml\nteam Team Falcon\n", encoding="utf-8")

    bios, problems = load_bios(bios_dir, config)

    # Nothing vanishes: the valid file and all three broken ones render, and no
    # bad file hides another.
    assert {bio.slug for bio in bios} == {"jane-doe", "bad-team", "no-headline", "broken-yaml"}
    assert {problem.path.rsplit("/", 1)[-1] for problem in problems} == {
        "bad-team.yml",
        "no-headline.yml",
        "broken-yaml.yml",
    }
    assert {bio.slug for bio in bios if bio.salvaged} == {"bad-team", "no-headline", "broken-yaml"}


def test_two_files_that_slug_to_the_same_page_both_render(bios_dir, config):
    # A student who saved the file twice, once with the wrong extension, would
    # otherwise silently overwrite their own page.
    write_bio(bios_dir, "jane-doe.yml")
    write_bio(bios_dir, "jane-doe.yaml")

    bios, problems = load_bios(bios_dir, config)

    assert sorted(bio.slug for bio in bios) == ["jane-doe", "jane-doe-2"]
    assert "another file already renders /jane-doe/" in messages(problems)
    duplicate = next(bio for bio in bios if bio.slug == "jane-doe-2")
    assert duplicate.url == "/jane-doe-2/"
    assert duplicate.salvaged is True


def test_the_unassigned_bucket_is_synthetic_and_never_configured(eleven_team_config):
    assert len(eleven_team_config.teams) == len(ELEVEN_TEAMS)
    assert eleven_team_config.team_names == ELEVEN_TEAM_NAMES
    # An instructor never adds it to site.yml, and it cannot be chosen by a bio.
    assert FALLBACK_TEAM_NAME not in eleven_team_config.team_names
    fallback = eleven_team_config.fallback_team
    assert fallback.name == FALLBACK_TEAM_NAME
    assert fallback.accent == FALLBACK_ACCENT
    assert "fix the 'team' value" in fallback.tagline


def test_group_by_team_follows_site_yml_order_and_keeps_empty_teams(bios_dir, eleven_team_config):
    write_bio(bios_dir, "jane-doe.yml", "name: Jane Doe\nteam: Team Eagle\nheadline: Backend engineer")
    write_bio(bios_dir, "bo-apple.yml", "name: Bo Apple\nteam: Team Falcon\nheadline: Frontend engineer")
    bios, problems = load_bios(bios_dir, eleven_team_config)
    assert problems == ()

    groups = group_by_team(eleven_team_config, bios)

    # Configured order, not bio order (the bios sort Apple then Doe) and not
    # only the populated teams: an empty team is a visible empty slot.
    assert [group.team.name for group in groups] == list(ELEVEN_TEAM_NAMES)
    assert {group.team.name: [bio.slug for bio in group.bios] for group in groups if group.count} == {
        "Team Falcon": ["bo-apple"],
        "Team Eagle": ["jane-doe"],
    }
    assert sum(1 for group in groups if group.count == 0) == len(ELEVEN_TEAMS) - 2


def test_group_by_team_appends_a_trailing_unassigned_group_for_an_unresolved_team(
    bios_dir, eleven_team_config
):
    write_bio(bios_dir, "jane-doe.yml", "name: Jane Doe\nteam: Team Falcon\nheadline: Backend engineer")
    write_bio(bios_dir, "bo-apple.yml", "name: Bo Apple\nteam: Team Penguin\nheadline: Frontend engineer")
    bios, problems = load_bios(bios_dir, eleven_team_config)
    assert problems

    groups = group_by_team(eleven_team_config, bios)

    assert len(groups) == len(ELEVEN_TEAMS) + 1
    trailing = groups[-1]
    assert trailing.team.name == FALLBACK_TEAM_NAME
    assert trailing.team.accent == FALLBACK_ACCENT
    assert [bio.slug for bio in trailing.bios] == ["bo-apple"]
    # The real teams keep their own bios.
    assert [bio.slug for bio in groups[0].bios] == ["jane-doe"]


def test_group_by_team_appends_nothing_when_every_team_resolves(bios_dir, eleven_team_config):
    write_bio(bios_dir, "jane-doe.yml", "name: Jane Doe\nteam: Team Falcon\nheadline: Backend engineer")
    bios, problems = load_bios(bios_dir, eleven_team_config)
    assert problems == ()

    groups = group_by_team(eleven_team_config, bios)

    assert len(groups) == len(ELEVEN_TEAMS)
    assert FALLBACK_TEAM_NAME not in [group.team.name for group in groups]


def test_build_is_lenient_by_default_so_one_bad_file_cannot_empty_the_site(bios_dir, config, tmp_path):
    write_bio(bios_dir, "jane-doe.yml")
    write_bio(
        bios_dir,
        "bo-apple.yml",
        "name: Bo Apple\nteam: Team Penguin\nheadline: Frontend engineer",
    )
    out = tmp_path / "dist"

    result = build(bios_dir, config, out)

    assert (out / "index.html").is_file()
    assert (out / "jane-doe" / "index.html").is_file()
    # The broken bio still gets a page, in the Unassigned bucket.
    broken_page = out / "bo-apple" / "index.html"
    assert broken_page.is_file()
    assert FALLBACK_TEAM_NAME in broken_page.read_text(encoding="utf-8")
    assert result.bios == 2
    assert result.problems
    assert result.salvaged == 1


def test_build_counts_only_configured_teams_on_the_roster(bios_dir, eleven_team_config, tmp_path):
    write_bio(bios_dir, "bo-apple.yml", "name: Bo Apple\nteam: Team Penguin\nheadline: Frontend engineer")
    out = tmp_path / "dist"

    result = build(bios_dir, eleven_team_config, out)

    # Unassigned is a defect bucket, not a team on the roster.
    assert f"across {len(ELEVEN_TEAMS)} teams" in (out / "404.html").read_text(encoding="utf-8")
    assert result.salvaged == 1


def test_build_with_strict_refuses_and_carries_the_problems(bios_dir, config, tmp_path):
    write_bio(bios_dir, "jane-doe.yml")
    write_bio(
        bios_dir,
        "bo-apple.yml",
        "name: Bo Apple\nteam: Team Penguin\nheadline: Frontend engineer",
    )
    out = tmp_path / "dist"

    with pytest.raises(BuildError) as excinfo:
        build(bios_dir, config, out, strict=True)

    assert "Team Penguin" in messages(excinfo.value.problems)
    # Nothing is rendered at all: strict means the whole build stops.
    assert not out.exists()


def test_build_of_a_clean_directory_reports_no_salvage(bios_dir, config, tmp_path):
    write_bio(bios_dir, "jane-doe.yml")
    out = tmp_path / "dist"

    result = build(bios_dir, config, out, strict=True)

    assert result.problems == ()
    assert result.salvaged == 0
    assert result.bios == 1
    assert (out / "index.html").is_file()


def test_validate_fails_on_a_broken_bio_so_the_pull_request_goes_red(
    bios_dir, config_path, tmp_path, capsys
):
    write_bio(bios_dir, "jane-doe.yml")
    write_bio(
        bios_dir,
        "bo-apple.yml",
        "name: Bo Apple\nteam: Team Penguin\nheadline: Frontend engineer",
    )

    status = main(["validate", "--bios", str(bios_dir), "--config", str(config_path)])

    assert status == 1
    assert "Team Penguin" in capsys.readouterr().err


def test_validate_passes_when_every_bio_is_clean(bios_dir, config_path, capsys):
    write_bio(bios_dir, "jane-doe.yml")

    status = main(["validate", "--bios", str(bios_dir), "--config", str(config_path)])

    assert status == 0
    assert "1 bio file(s) valid." in capsys.readouterr().out


def test_build_warns_about_fallbacks_but_still_ships_the_site(bios_dir, config_path, tmp_path, capsys):
    write_bio(bios_dir, "jane-doe.yml")
    write_bio(
        bios_dir,
        "bo-apple.yml",
        "name: Bo Apple\nteam: Team Penguin\nheadline: Frontend engineer",
    )
    out = tmp_path / "dist"

    status = main(
        ["build", "--bios", str(bios_dir), "--config", str(config_path), "--out", str(out)]
    )

    assert status == 0
    captured = capsys.readouterr()
    assert "warning" in captured.err
    assert "fallback values" in captured.err
    # The warning points at the command that does treat this as a failure.
    assert "generator validate" in captured.err
    assert (out / "index.html").is_file()
    assert (out / "bo-apple" / "index.html").is_file()


def test_build_with_strict_flag_fails_and_writes_nothing(bios_dir, config_path, tmp_path, capsys):
    write_bio(
        bios_dir,
        "bo-apple.yml",
        "name: Bo Apple\nteam: Team Penguin\nheadline: Frontend engineer",
    )
    out = tmp_path / "dist"

    status = main(
        ["build", "--strict", "--bios", str(bios_dir), "--config", str(config_path), "--out", str(out)]
    )

    assert status == 1
    assert "Team Penguin" in capsys.readouterr().err
    assert not out.exists()


def test_slugify_folds_accents_to_the_expected_filename():
    assert slugify("José Álvarez") == "jose-alvarez"


def test_initials_fall_back_to_a_single_letter():
    assert initials("José Álvarez") == "JÁ"
    assert initials("Prince") == "P"


def test_hue_is_stable_across_processes():
    # Pinned rather than compared to itself: a per-process salted hash (or a
    # changed algorithm) would churn the generated CSS between deploys.
    assert hue_for("jane-doe") == 276
    assert hue_for("ada-lovelace") == 145


def test_site_config_without_teams_is_a_config_error(tmp_path):
    path = tmp_path / "site.yml"
    path.write_text("title: No Teams Here\n", encoding="utf-8")

    with pytest.raises(ConfigError):
        SiteConfig.load(path)
