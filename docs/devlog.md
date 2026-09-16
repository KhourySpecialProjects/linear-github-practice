# Devlog

Newest entry first. Each entry records what shipped, the decisions behind it,
and what is still outstanding.

## 2026-09-16 — Scaffold, YAML cutover, fallbacks, and template packaging

Seven commits, `132c02e` through `a8958f1`, all pushed to `testing`. CI
(`Validate bios`, `Build site`) passed on the push. 62 tests, 36 tracked files.

### What shipped

**The app.** A static professional bio aggregator. One YAML file per student in
`bios/`, rendered by a small Jinja generator into `dist/` and served by nginx.
Whatever files exist at build time are the site.

- `generator/` — `bios.py` (parse and validate), `config.py` (`site.yml`),
  `render.py` (group by team, render pages), `text.py`, `__main__.py`
  (`validate`, `build`, `serve`).
- Multi-stage `Dockerfile`: `python:3.12-slim` builds, `nginx:1.27-alpine-slim`
  serves. **12.4 MB final image, 6.5 s cold build, 0.65 s cached.**
- `docker-compose.yml` for local dev on `http://localhost:8088`,
  `docker-compose.coolify.yml` for the deployed environment,
  `deploy/nginx.conf`.
- `.github/workflows/ci.yml` — `validate-bios` and `build-site`, both under a
  minute, no Docker build in CI.
- `scripts/roster.py` — turns a roster CSV into Linear issue text and the
  pre-assigned review ring.
- Docs: `student-quickstart.md`, `in-class-exercise.md` (50-minute runbook),
  `instructor-setup.md`, `bios/README.md`, `bios/TEMPLATE.yml`.

**Bio format is pure YAML** (`4689e7f`). Files were almost entirely structured
data with a short prose tail, so the `.md` extension and the `---` fence carried
no weight. A bio is now `bios/first-last.yml`: one YAML mapping whose required
`about` block scalar is still rendered as Markdown.

Moving prose into YAML moves students into YAML's sharpest corner, so the
validator reports the specific mistake rather than PyYAML's wording: tab
indentation, an unquoted `': '` in a value, a leftover `---` fence, an empty
file, a non-mapping document, `about` written as a nested mapping, and an
over-indented paragraph that Markdown would render as a grey code block.

**Fallback values, and 11 teams** (`529b392`). `parse_bio` always returns a
renderable `Bio`. A broken file renders with substituted values — name derived
from the filename, an `Unassigned` team group, placeholder headline and about
text, bad `focus`/`links` entries dropped — and every substitution is reported.

`site.yml` lists 11 teams and nothing hardcodes the count.

**Self-contained, reusable docs** (`a3dff4f`, `a8958f1`). The docs no longer
link out to the playbooks repo; the rules a reader needs are written here, at
the step that needs them. Course-specific values live in one fill-in table in
`instructor-setup.md`. Setup now starts from **Use this template**, not an empty
directory and not a fork.

### Decisions worth remembering

| Decision | Why |
|---|---|
| One long-lived branch, `testing` | Matches the first deployed environment of the four-environment model without the promotion plumbing. No `main`, no `staging`, no `production`. |
| Python + Jinja to static, nginx to serve | Small image, fast rebuild, no npm. The runtime is literally static files. |
| One file per student, no shared index | 12–20 concurrent pull requests **cannot** conflict. The app globs the directory. |
| Pre-assigned review ring, 1 required approval | Keeps the review lesson while removing the "who reviews me?" stall that would blow the 50-minute budget. |
| **Strict where it teaches, resilient where it deploys** | `validate` (CI) exits 1 so a bad bio turns the PR red. `build` substitutes fallbacks and exits 0 so one file merged past the gate degrades one card instead of emptying the site. `build --strict` opts back in; the `Dockerfile` is deliberately not strict. |
| Template repository, not a fork | On a fork, GitHub's "Compare & pull request" banner defaults the base to the upstream repo, so a student would eventually open their bio PR against the template. Template generation has no upstream, and copies only the default branch — so a new class repo starts with `testing` as its only branch. |
| Teams are data | `site.yml` alone. Any number, any order. |

### Defects found by verification, not by review

- **A broken avatar URL left an empty circle.** Students will paste hosts that
  block hotlinking. `app.js` now swaps a failed image for the initials monogram.
- **The example bio pointed at a 2.3 MB original-resolution JPEG**, which also
  taught the wrong habit. Switched to a 140 KB thumbnail.
- **Port 8080 was already taken** on the author's machine by an unrelated
  container, so the live demo would have failed. Default is now 8088, overridable
  with `SITE_PORT`.
- **`docker compose up` without `--build` silently serves the previous build**,
  which is exactly the "I added my file and it isn't there" trap. Measured and
  documented.
- **`/assets/*` was cached `immutable` for a year with un-hashed filenames.** A
  redeploy left returning browsers pinned to a stale stylesheet — this was hit
  first-hand while changing the layout. Now `max-age=300`.
- **11 teams made a 5232 px column of whitespace** (436 px of chrome per team
  for one or two cards). Team panels now flow in a responsive grid: 3814 px.
- **"Teams represented: 12" versus "on the roster: 11"** — the `Unassigned`
  bucket was being counted as a twelfth team.

### Outstanding

Nothing below is blocked on code. All of it is configuration in GitHub, Linear,
or the deploy host, plus two open questions.

**Before the exercise can run**

- [ ] **Protect `testing`.** Currently unprotected
      (`branches/testing/protection` → 404): no required pull request, no
      required approval, no required checks. `Validate bios` and `Build site`
      have now run at least once, so they appear in the checks picker — the
      chicken-and-egg noted in `instructor-setup.md` §2 is resolved.
- [ ] **Merge settings.** Squash-only is off (merge commits and rebase merging
      are both still allowed) and auto-delete-head-branches is off.
- [ ] **Roster CSV**, then `python scripts/roster.py roster.csv` and `--ring`.
- [ ] **Create the Linear issues.** The `LGH` team has **zero** issues. One per
      student, titled `Add bio for <Full Name>`, with the assigned reviewer named
      in the description.
- [ ] **Verify the Linear branch-name automation end-to-end** with a throwaway
      branch whose name starts with the team key and an issue number. Never
      exercised yet.
- [ ] **Deploy.** No Coolify application exists, so `<deployed-url>` is still
      unassigned and the auto-deploy webhook has never fired. `docker-compose.coolify.yml`
      is written but has only been validated with `docker compose config`.
- [ ] **Student GitHub access** with Write, invitations accepted before class.
- [ ] **Seed one worked example** merged through the full workflow, so the site
      is never empty when students first load it (`instructor-setup.md` §8).

**Loose ends in the repo**

- [ ] **`bios/mark-fontenot.yml` is untracked**, so it is not on the remote and
      will not deploy. It validates cleanly. Landing it through the normal
      workflow — issue, branch, PR, review, squash merge — would double as the
      worked example above.
- [ ] **Oxford commas in existing prose.** A standing style preference was
      recorded for future writing. A retroactive sweep of what is already
      committed was started, then reverted as unrequested scope. A scan found 66
      candidate fragments across 13 files, of which perhaps half are genuine
      three-or-more-item lists; the rest are two-item lists and compound
      sentences. Do this only if the inconsistency is worth a commit.

**Open questions**

- [ ] **The repository is now public, but the docs still say `--private`.**
      `instructor-setup.md` §1 and `README.md` both pass `--private` to
      `gh repo create`, and §1 still warns about a private repo being missed in
      an app's repository list. Decide what an adopting instructor should
      default to, and make the docs match.
- [ ] **This repo is both the template and a course instance.** `site.yml`
      carries one school and term, `bios/` carries four example bios, and
      `isTemplate` is now true — so every future class inherits whatever is
      here. Either keep it as the canonical example and accept that adopters
      delete content, or strip `site.yml` to neutral placeholders and cut the
      examples to one. Related: never merge a class's student bios into the
      template (`instructor-setup.md`, "Maintaining the template").

**Resolved since it was raised**

- The nine workflow playbooks are now published on `main` in
  `practicum-playbooks`. This no longer affects the exercise either way: the
  docs here were deliberately made independent of that repo, and no longer link
  to it.
