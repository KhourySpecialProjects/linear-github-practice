"""Tests for the validator contract that gates every student pull request.

The exercise lives or dies on `python -m generator validate` telling a student
exactly what to fix, so these tests assert on the *problems* a bad bio file
produces (by substring, so wording can be improved without breaking the suite)
and on the values a template is allowed to read off a good one.

A bio is now a plain YAML mapping, so YAML's own sharp edges - tabs, an
unquoted ``": "`` inside a value, an empty file, a block scalar written as a
nested mapping - are part of the contract and get their own tests.
"""

from __future__ import annotations

import textwrap

import pytest

from generator.bios import (
    ABOUT_MAX,
    ABOUT_MIN,
    FOCUS_ITEM_MAX,
    FOCUS_MAX,
    HEADLINE_MAX,
    Link,
    load_bios,
    parse_bio,
)
from generator.config import ConfigError, SiteConfig
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


@pytest.fixture
def config(tmp_path):
    """A real SiteConfig, loaded from YAML, so the loader is exercised too."""
    path = tmp_path / "site.yml"
    path.write_text(SITE_YML, encoding="utf-8")
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
    assert bio is not None
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
def test_each_missing_required_key_names_the_key(bios_dir, config, missing):
    fields = "\n".join(line for key, line in REQUIRED_FIELDS.items() if key != missing)
    path = write_bio(bios_dir, "jane-doe.yml", fields)

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert f"missing required key '{missing}'" in messages(problems)


def test_missing_about_shows_the_block_scalar_shape(bios_dir, config):
    path = write_bio(bios_dir, "jane-doe.yml", MINIMAL, about=None)

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "missing required key 'about'" in text
    # The student is shown the shape, because 'about: |' is the part they get wrong.
    assert "about: |" in text
    assert "Two or three sentences" in text


def test_unknown_key_is_rejected_and_lists_the_allowed_keys(bios_dir, config):
    path = write_bio(bios_dir, "jane-doe.yml", f"{MINIMAL}\ntwitter: '@janedoe'")

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "unknown key 'twitter'" in text
    # The allowed-key list is spelled out rather than hinted at.
    assert "fun_fact" in text
    assert "pronouns" in text


def test_unknown_team_lists_the_course_teams(bios_dir, config):
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

    assert bio is None
    text = messages(problems)
    assert "Team Penguin" in text
    assert "Team Falcon" in text
    assert "Team Kestrel" in text


def test_filename_must_match_the_name_field(bios_dir, config):
    wrong = write_bio(bios_dir, "jane-doe.yml", "name: Jane Zebra\n" + "\n".join(
        line for key, line in REQUIRED_FIELDS.items() if key != "name"
    ))

    bio, problems = parse_bio(wrong, config)

    assert bio is None
    text = messages(problems)
    assert "jane-zebra.yml" in text
    assert "Jane Zebra" in text

    # Control: the identical bio under the matching filename is accepted, so
    # this test cannot pass just because something else is broken.
    right = write_bio(bios_dir, "jane-zebra.yml", "name: Jane Zebra\n" + "\n".join(
        line for key, line in REQUIRED_FIELDS.items() if key != "name"
    ))
    good, no_problems = parse_bio(right, config)
    assert no_problems == []
    assert good is not None and good.slug == "jane-zebra"


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
def test_bad_filenames_are_rejected(bios_dir, config, filename):
    path = write_bio(bios_dir, filename)

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert "filename must be lowercase" in messages(problems)


def test_yaml_extension_is_reported_by_the_loader_not_silently_skipped(bios_dir, config):
    # load_bios globs '*.y*ml' precisely so a student who saves '.yaml' gets a
    # filename error instead of a mysteriously missing bio page.
    write_bio(bios_dir, "jane-doe.yaml")

    bios, problems = load_bios(bios_dir, config)

    assert bios == ()
    assert [problem.path.rsplit("/", 1)[-1] for problem in problems] == ["jane-doe.yaml"]
    assert "filename must be lowercase" in messages(problems)


def test_about_shorter_than_the_minimum_is_rejected(bios_dir, config):
    path = write_bio(bios_dir, "jane-doe.yml", about="Too short.")

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert f"at least {ABOUT_MIN}" in messages(problems)


def test_about_of_exactly_the_minimum_length_is_valid(bios_dir, config):
    exact = "Exactly forty characters of honest prose"
    assert len(exact) == ABOUT_MIN

    path = write_bio(bios_dir, "jane-doe.yml", about=exact)

    bio, problems = parse_bio(path, config)

    assert problems == []
    assert bio is not None


def test_about_longer_than_the_maximum_is_rejected(bios_dir, config):
    path = write_bio(bios_dir, "jane-doe.yml", about="Detail about the work. " * 120)

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert f"under {ABOUT_MAX}" in messages(problems)


def test_headline_longer_than_the_maximum_is_rejected(bios_dir, config):
    long_headline = "Backend engineer " * 8
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"name: Jane Doe\nteam: Team Falcon\nheadline: {long_headline.strip()}",
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert f"under {HEADLINE_MAX}" in messages(problems)


def test_too_many_focus_entries_are_rejected(bios_dir, config):
    # Eight entries is a literal over-run of the documented limit of six: if the
    # cap were quietly raised, this bio would be accepted and the test would fail.
    entries = "\n".join(f"  - Skill {index}" for index in range(8))
    path = write_bio(bios_dir, "jane-doe.yml", f"{MINIMAL}\nfocus:\n{entries}")

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert f"at most {FOCUS_MAX}" in messages(problems)


def test_focus_entry_longer_than_a_chip_is_rejected(bios_dir, config):
    # 'focus' renders as small chips, so a sentence smuggled into one is a
    # layout bug: 34 characters is a literal over-run of the 24-character rule.
    long_entry = "Distributed systems and caching"
    assert len(long_entry) > FOCUS_ITEM_MAX
    path = write_bio(bios_dir, "jane-doe.yml", f"{MINIMAL}\nfocus:\n  - {long_entry}")

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert long_entry in text
    assert f"under {FOCUS_ITEM_MAX} characters" in text


def test_link_without_a_scheme_is_rejected(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"{MINIMAL}\nlinks:\n  GitHub: github.com/janedoe",
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "GitHub" in text
    assert "https://" in text


def test_raw_script_in_about_is_rejected(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        about="Backend engineer. <script>alert('hi')</script> And some more prose here.",
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert "HTML/JavaScript" in messages(problems)


def test_tab_indentation_is_reported_in_terms_of_tabs_and_spaces(bios_dir, config):
    path = bios_dir / "jane-doe.yml"
    path.write_text(f"{MINIMAL}\nfocus:\n\t- Python\nabout: |\n  {ABOUT.strip()}\n", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    # Tabs get their own instruction instead of leaking PyYAML's wording, which
    # points at a column rather than telling the student what to type.
    assert "replace tabs with two spaces" in text
    assert "invalid YAML" not in text


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

    assert bio is None
    text = messages(problems)
    assert "invalid YAML at line" in text
    assert "quotes" in text


def test_empty_file_points_at_the_template(bios_dir, config):
    path = bios_dir / "jane-doe.yml"
    path.write_text("", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "empty" in text
    assert "TEMPLATE.yml" in text


def test_over_indented_paragraph_is_caught_instead_of_rendering_as_a_code_block(bios_dir, config):
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

    assert bio is None
    text = messages(problems)
    assert "code block" in text
    assert "two spaces" in text


def test_a_fenced_code_block_in_about_is_rejected(bios_dir, config):
    path = bios_dir / "jane-doe.yml"
    path.write_text(
        f"{MINIMAL}\nabout: |\n  How I work, which is a long enough sentence to pass:\n\n"
        "  ```\n  git commit -m \"wip\"\n  ```\n",
        encoding="utf-8",
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    assert "code block" in messages(problems)


def test_a_leftover_front_matter_fence_is_explained(bios_dir, config):
    """Opening and closing '---' is two YAML documents, whose native error is opaque."""
    path = bios_dir / "jane-doe.yml"
    path.write_text(f"---\n{MINIMAL}\n{ONE_LINE_ABOUT}---\n", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "remove the '---' lines" in text


def test_a_single_leading_document_marker_is_still_valid_yaml(bios_dir, config):
    """One '---' is legal YAML, so it must not be swept up by the fence check."""
    path = bios_dir / "jane-doe.yml"
    path.write_text(f"---\n{MINIMAL}\n{ONE_LINE_ABOUT}", encoding="utf-8")

    bio, problems = parse_bio(path, config)

    assert problems == []
    assert bio is not None


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

    assert bio is None
    assert "'key: value' fields" in messages(problems)


def test_about_written_as_a_nested_mapping_shows_the_block_scalar_shape(bios_dir, config):
    path = write_bio(
        bios_dir,
        "jane-doe.yml",
        f"{MINIMAL}\nabout:\n  summary: I work on APIs and the infrastructure underneath them.",
        about=None,
    )

    bio, problems = parse_bio(path, config)

    assert bio is None
    text = messages(problems)
    assert "'about' must be a block of text" in text
    assert "about: |" in text


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


def test_load_bios_accumulates_problems_from_every_bad_file(bios_dir, config):
    write_bio(bios_dir, "jane-doe.yml")
    write_bio(
        bios_dir,
        "bad-team.yml",
        "name: Bad Team\nteam: Team Penguin\nheadline: Backend engineer",
    )
    write_bio(bios_dir, "no-headline.yml", "name: No Headline\nteam: Team Falcon")
    (bios_dir / "broken-yaml.yml").write_text("name: Broken Yaml\nteam Team Falcon\n", encoding="utf-8")

    bios, problems = load_bios(bios_dir, config)

    # The valid file still loads, and no bad file hides another.
    assert [bio.slug for bio in bios] == ["jane-doe"]
    assert {problem.path.rsplit("/", 1)[-1] for problem in problems} == {
        "bad-team.yml",
        "no-headline.yml",
        "broken-yaml.yml",
    }


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
