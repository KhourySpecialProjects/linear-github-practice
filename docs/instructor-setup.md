# Instructor Setup

One-time setup for the bio-aggregator exercise: GitHub repository, Linear team,
a deployment host, and the two files you own (`site.yml` and your roster CSV).
Class-day choreography is in [in-class-exercise.md](./in-class-exercise.md).

## Fill these in

This table is the only place course-specific values live. Everything else in
this repo's documentation uses the placeholders. **A new instructor replaces the
`This instance` column** — nothing else in this file needs editing to move the
exercise to another school, org or Linear workspace.

| Placeholder | What it is | This instance |
|---|---|---|
| `<org>/<repo>` | GitHub owner and repository for this exercise, as used by `gh` commands and clone URLs | `KhourySpecialProjects/linear-github-practice` |
| `<KEY>` | Linear team key, uppercase — the `ENG` in `ENG-142`. It becomes the prefix of every branch name students copy out of Linear. | `LGH` |
| `<deployed-url>` | URL the deployed site is served from | Not yet assigned — paste it here once your host gives you a domain, and give it to students |
| Linear workspace | The workspace holding the team above | `khoury-practicum` |
| `site.yml`: `title`, `tagline`, `course`, `footer` | The site's own name, one-line description, course label and footer line. School and term names belong here, not in the docs. | Set for the shipped course; edit in `site.yml` (see [section 6](#6-tune-siteyml-before-class)) |
| `site.yml`: `teams` | The team names, taglines and accent colours a bio's `team` is checked against | Eleven shipped teams; edit in `site.yml` |

Everything else below is concrete.

## Goal

`<org>/<repo>` exists with `testing` as its only branch — default, protected,
and auto-deploying to `<deployed-url>` — plus one Linear issue per student in
team `<KEY>`.

## This repo has one environment on purpose

Real client projects usually promote a change through several deployed
environments, merging forward one step at a time. This teaching repo
deliberately stops at the first deployed one: `testing` is the default branch,
the protected branch, and the branch the host deploys. There is no `staging`, no
`production`, no `main`. Say this once in class so students do not go looking
for the other branches.

## 1. Create the repository

The local repo starts with no commits and no remote. Make `testing` the only
branch from the very first commit, so it becomes the default automatically:

```sh
cd linear-github-practice
git switch -c testing
git add -A
git commit -m "Add bio aggregator scaffold"
gh repo create <org>/<repo> --private --source . --remote origin
git push -u origin testing
```

Then confirm:

```sh
gh repo view <org>/<repo> --json defaultBranchRef
```

It must report `testing`. If not:
`gh repo edit <org>/<repo> --default-branch testing`.

The repository must be visible to:

- the students' GitHub team, with **Write** access (they push branches, they
  never push to `testing`);
- your **Linear** GitHub app (branch/PR/merge automation);
- your deploy host's GitHub app or webhook (build and deploy on push).

If those apps are installed at the organization level, confirm this repo is in
each app's repository list — a new private repo is the usual thing they miss.

## 2. Protect `testing`

Settings -> Branches -> add a rule for `testing`:

- [ ] Require a pull request before merging
- [ ] Require approvals: **1**
- [ ] Require status checks to pass: the two jobs in
      `.github/workflows/ci.yml` — job ids `validate-bios` and `build-site`,
      listed in GitHub's picker under their display names **Validate bios** and
      **Build site**. They appear in the picker only after one PR has run them,
      so open a throwaway PR first if the list is empty.
- [ ] Require branches to be up to date before merging: off (unnecessary here,
      and it forces avoidable re-runs with 20 concurrent PRs)
- [ ] Do not allow bypassing the above settings: **off** — you keep admin
      bypass for stragglers at minute 45
- [ ] Block force pushes and deletions

Settings -> General -> Pull Requests:

- [ ] Allow squash merging **only** (uncheck merge commits and rebase merging)
- [ ] Automatically delete head branches

This rule is the whole lesson: nobody pushes to a deployed branch, and every
change on the live site arrives through a reviewed, squash-merged pull request
whose branch is deleted afterwards.

## 3. Linear

- Your Linear workspace, team key `<KEY>` (see the table above).
- Confirm the Linear GitHub integration is installed and can see this repo.
  Nothing repo-local needs configuring.
- Create one issue per student, titled exactly `Add bio for <Full Name>`, in
  **Todo**, assigned to that student. Generate the titles and paste-ready
  descriptions:

  ```sh
  python scripts/roster.py roster.csv
  python scripts/roster.py roster.csv --ring
  ```

  The description names the student's file, their team, and their assigned
  reviewer — the ring is the sorted roster, student *n* reviews student *n+1*,
  last reviews first. Naming the reviewer on the issue is what stops 20 students
  from hunting for one in class.
- The automation students rely on is branch-name based:
  Linear's **Copy git branch name** yields a branch like
  `abc-12-add-bio-for-jane-doe`, where `abc-12` is the team key plus the issue
  number — so in your course the prefix is `<KEY>` lowercased. That issue ID in
  the branch name is what moves the issue to **In Progress** when the branch is
  pushed, **In Review** when the PR opens, and **Done** when it merges. Nobody
  pastes an issue ID by hand.
- The habits this exercise asks for are short enough to say out loud: branch
  names come from Linear rather than from imagination, one commit does one
  thing and its message says what it does in the imperative, a review is an
  explicit verdict on a diff you actually read, and a protected branch is only
  ever changed by merging an approved pull request.

## 4. Deploy the site

### What the repo needs from any host

The repo is deliberately undemanding, so any of a dozen hosts will do. What it
requires:

- **Build the image.** Either build the `Dockerfile` directly, or run
  `docker-compose.coolify.yml`, which builds the same `Dockerfile` and adds a
  restart policy and a healthcheck.
- **Serve port 80.** The runtime stage is nginx (`deploy/nginx.conf`), which
  listens on 80 and serves the pre-rendered HTML. `docker-compose.coolify.yml`
  only `expose`s that port on the internal Docker network, so the host's proxy
  is expected to route the domain to it and terminate TLS.
- **Redeploy on push to `testing`.** A merge into the integration branch must
  rebuild and swap the container; the rebuild is what re-runs
  `python -m generator build`. If the deploy is manual, the class does not see
  their bios appear.
- **No environment variables and no secrets.** The site is static and
  everything it renders is in the repo.
- A liveness probe, if the host wants one: `GET /healthz` returns `200 ok`.

Alternatives to the walkthrough below: any PaaS that builds a `Dockerfile` on
push, or a plain Docker host where a push webhook pulls the new commit,
rebuilds the image and restarts the container behind your own proxy.

### Worked example: Coolify

1. New **Application** in your Coolify project, source = `<org>/<repo>` via the
   Coolify GitHub app.
2. Build pack: **Docker Compose**, compose file `docker-compose.coolify.yml`.
3. Branch: **`testing`**.
4. Domain: set it, and record it as `<deployed-url>` in the table above.
5. Enable **auto-deploy** so the GitHub webhook rebuilds on every merge to
   `testing`.
6. Deploy once now and load the URL. No environment variables or secrets are
   needed.

Whatever the host, keep the deploy a consequence of a merge rather than a
button someone remembers to press: that is what makes the protected branch mean
something. Nobody uploads files to the server by hand.

## 5. Optional: other runners

Both jobs in `.github/workflows/ci.yml` run on `ubuntu-latest`. If your org has
self-hosted or third-party runners, point `runs-on` at them instead — the
commented line above each `runs-on` is where. Not required: the two checks take
seconds on GitHub-hosted runners, so there is nothing here worth optimising.

## 6. Tune `site.yml` before class

`site.yml` is instructor-owned; students never touch it, which is why their PRs
cannot conflict. Edit team names, taglines and accents to match your roster:

```yaml
teams:
  - name: Team Falcon
    tagline: Fast feedback, small pull requests
    accent: "#7c5cff"
```

Shipped teams, in the order the site groups them: Team Falcon (`#7c5cff`), Team
Kestrel (`#00b6a4`), Team Osprey (`#ff7a45`), Team Harrier (`#3b82f6`), Team
Merlin (`#ec4899`), Team Goshawk (`#22c55e`), Team Kite (`#f59e0b`), Team
Caracara (`#8b5cf6`), Team Peregrine (`#06b6d4`), Team Condor (`#ef4444`) and
Team Eagle (`#14b8a6`).

**The team count is not fixed anywhere in the code.** Teams are data: add,
rename or remove them by editing `site.yml` alone, in any number and any order,
and the site regroups on the next build. Nothing in `generator/` knows there
are eleven, and `site.yml` is the only list a bio's `team` is checked against.

A bio's `team` must match one of those names (case-insensitively), so if you
rename a team, rename it *before* the roster CSV goes out — and re-run
`python -m generator validate` afterwards, since existing bios will fail
against a renamed team. They will not disappear from the site: a bio whose
`team` no longer resolves renders in a trailing **Unassigned** group instead
(see below).

Also update `title`, `tagline`, `course` and `footer` for the term — those four
strings are where the school and semester are named.

## 7. Strict where it teaches, resilient where it deploys

One rule, two behaviours: the check that grades a pull request is strict, and
the build that ships the site is not. A student's bad bio still turns their PR
red, and a bad bio that got merged anyway degrades one card instead of taking
the whole site down.

| Command or file | Behaviour on a problem | Why |
|---|---|---|
| `python -m generator validate` | Prints every problem, exits **1** | The gate. This is what CI runs on every pull request, so the review lesson is intact. |
| `python -m generator build` | Substitutes fallback values, prints a **warning**, exits **0** | The deployed site must survive one bad file that got merged — for example via your admin bypass at minute 45. |
| `python -m generator build --strict` | Exits **1**, renders nothing | Opt-in for anyone who wants a build to fail. `serve` takes `--strict` too. |
| `Dockerfile` | Runs `build` **without** `--strict` | On purpose: a deploy cannot be taken down by one malformed bio. |
| `.github/workflows/ci.yml`, job `validate-bios` | Runs `validate` | Unchanged — still the hard gate on `testing`. |

### Spotting a degraded bio

A resilient build is loud, not silent. It prints, to stderr:

```
warning: 1 problem(s) in bios/; 1 bio(s) rendered with fallback values:
  bios/jane-doe.yml: team 'Team Flacon' is not one of the course teams - use one of: Team Falcon, Team Kestrel, Team Osprey, Team Harrier, Team Merlin, Team Goshawk, Team Kite, Team Caracara, Team Peregrine, Team Condor, Team Eagle
The site was built anyway. Run 'python -m generator validate' to treat these as failures, which is what CI does on every pull request.
```

That warning appears in the deploy log for the deploy that shipped it, so the
log is where you check after class. On the site, a bio whose `team` did not
resolve is grouped under a trailing **Unassigned** heading after your real
teams; `Unassigned` is not in `site.yml` and you never add it. A field that
could not be read shows placeholder text — `Bio still needs a headline`, or an
`about` that tells the reader to run the validator.

To see every problem as a failure, at any time:

```sh
python -m generator validate
python -m generator build --strict     # same verdict, and renders nothing
```

## 8. Seed one worked example

Merge one real bio through the full workflow yourself — issue, branch, PR,
self-approve with admin bypass, squash merge — before class. It proves the whole
pipeline end to end and means the site is never empty when students first load
it.

## Adapting this repo to your course

Every choice below is a default, not a constraint. Each row names the file and
the place inside it to change.

| Decision this repo ships with | Where to change it |
|---|---|
| Integration branch is named `testing` | `.github/workflows/ci.yml` — the `pull_request.branches` and `push.branches` filters, both `[testing]`; the branch-protection rule (section 2); the branch your deploy host tracks (section 4); the `footer` line in `site.yml`, which names the branch; and the branch named throughout `docs/` and `README.md`. |
| Eleven teams, and the site's title/tagline/course/footer | `site.yml`, and nothing else. Any number of teams, in any order. |
| One required approving review | The branch-protection rule's **Require approvals** count (section 2). |
| Reviewers pre-assigned as a ring (student *n* reviews *n+1*, last reviews first) | `scripts/roster.py` — the ring is closed in `build_records` with `ordered[(index + 1) % len(ordered)]`, and printed by `--ring`. Assign reviewers some other way and the rest of the exercise is unaffected. |
| Issue titles read `Add bio for <Full Name>` | `scripts/roster.py` — the `issue_title` value in `build_records`. The title is instructor-facing only; nothing in `generator/` parses it. |
| Required keys `name`, `team`, `headline`, `about`; optional `pronouns`, `location`, `focus`, `links`, `avatar`, `fun_fact`; and the limits (headline ≤ 90, `about` 40–2000, ≤ 6 focus items of ≤ 24 characters each) | The constants at the top of `generator/bios.py`: `REQUIRED_KEYS`, `ALLOWED_KEYS`, `HEADLINE_MAX`, `ABOUT_MIN`, `ABOUT_MAX`, `FOCUS_MAX`, `FOCUS_ITEM_MAX`. Changing them means updating [`bios/TEMPLATE.yml`](../bios/TEMPLATE.yml) so students see the new shape, and `tests/test_bios.py`, which imports those constants. |
| Local preview on port 8088 | `docker-compose.yml` — the `"${SITE_PORT:-8088}:80"` mapping; students can already override it per-run with `SITE_PORT=9090`. |

If your course has its own written standards for commits, reviews or
deployments, link them from [`README.md`](../README.md) and say in class which
one wins where they disagree. This repo does not assume any exist.

## Verification

- [ ] `gh repo view <org>/<repo> --json defaultBranchRef` reports `testing`
- [ ] A test PR into `testing` cannot merge without 1 approval and both checks
- [ ] `validate-bios` fails on a deliberately broken bio and annotates the file
- [ ] `python -m generator build` on that same broken bio exits 0 with a `warning:` line, and `python -m generator build --strict` exits 1
- [ ] Pushing to `testing` triggers a deploy and `<deployed-url>` serves the site
- [ ] A test branch whose name starts with your team key and an issue number, `abc-1-...`, moves its Linear issue automatically
- [ ] Every student can see the repo and has accepted their invitation
- [ ] `python scripts/roster.py roster.csv --ring` output matches the issues you created

## Notes

- Do not create `main`. An accidental `main` becomes the default branch and
  silently breaks the protection rule and the deploy webhook.
- The bio loader skips `bios/TEMPLATE.yml`, and it only reads YAML files, so
  `bios/README.md` is never picked up either — you can document freely in both.
- Rerunning the exercise next term: delete the student bios from `bios/` in one
  instructor PR, keep everything else, re-run `scripts/roster.py` with the new
  roster.
