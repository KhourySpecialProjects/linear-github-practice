# Instructor Setup

One-time setup for the bio-aggregator exercise: GitHub repository, Linear team,
Coolify app, and the two files you own. Class-day choreography is in
[in-class-exercise.md](./in-class-exercise.md).

## Fill these in

| Placeholder | Value | Notes |
|---|---|---|
| `KhourySpecialProjects/linear-github-practice` | repo slug | The org is assumed to be `KhourySpecialProjects` (where `practicum-playbooks` lives). Confirm before you create the repo. |
| `<deployed-url>` | Coolify domain for this app | Assigned when you create the Coolify application; paste it back into this file and give it to students. |

Everything else below is concrete.

## Goal

`KhourySpecialProjects/linear-github-practice` exists with `testing` as its
only branch — default, protected, and auto-deploying to `<deployed-url>` — plus
one Linear issue per student in team LGH.

## This repo has one environment on purpose

The playbooks describe Local -> Testing -> Staging -> Production for real client
projects. This teaching repo stops at the first deployed environment: `testing`
is the default branch, the protected branch, and the branch Coolify deploys.
There is no `staging`, no `production`, no `main`. Say this once in class so
students do not go looking for the other branches.

## 1. Create the repository

The local repo starts with no commits and no remote. Make `testing` the only
branch from the very first commit, so it becomes the default automatically:

```sh
cd linear-github-practice
git switch -c testing
git add -A
git commit -m "Add bio aggregator scaffold"
gh repo create KhourySpecialProjects/linear-github-practice --private --source . --remote origin
git push -u origin testing
```

Then confirm:

```sh
gh repo view KhourySpecialProjects/linear-github-practice --json defaultBranchRef
```

It must report `testing`. If not:
`gh repo edit KhourySpecialProjects/linear-github-practice --default-branch testing`.

The repository must be visible to:

- the students' GitHub team, with **Write** access (they push branches, they
  never push to `testing`);
- the org-wide **Linear** GitHub app (branch/PR/merge automation);
- the org-wide **Coolify** GitHub app (build and deploy webhooks).

Both apps are installed at the organization level, but confirm this repo is in
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

## 3. Linear

- Workspace `khoury-practicum`, team key **LGH**.
- Confirm the Linear GitHub integration is installed org-wide and can see this
  repo. Nothing repo-local needs configuring.
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
  Linear's **Copy git branch name** yields `lgh-12-add-bio-for-jane-doe`, and
  the `lgh-12` prefix moves the issue to **In Progress** when the branch is
  pushed, **In Review** when the PR opens, and **Done** when it merges. Nobody
  pastes an issue ID by hand. See
  [Developer Expectations](../../practicum-playbooks/developer-expectations.md).

## 4. Coolify

1. New **Application** in the practicum Coolify project, source =
   `KhourySpecialProjects/linear-github-practice` via the Coolify GitHub app.
2. Build pack: **Docker Compose**, compose file `docker-compose.coolify.yml`.
3. Branch: **`testing`**.
4. Domain: set it, and record it here as `<deployed-url>`.
5. Enable **auto-deploy** so the GitHub webhook rebuilds on every merge to
   `testing`.
6. Deploy once now and load the URL. No environment variables or secrets are
   needed — the site is static and everything it renders is in the repo.

Background: [Environments & Deployment](../../practicum-playbooks/environments-and-deployment.md).

## 5. Optional: Blacksmith runners

If this repo should run its Actions on Blacksmith, follow
[Blacksmith Setup](../../practicum-playbooks/blacksmith-setup.md): add the repo
to the org app's approved list and update the workflow's `runs-on`. Not
required — the exercise runs fine on GitHub-hosted runners, and the two checks
take seconds.

## 6. Tune `site.yml` before class

`site.yml` is instructor-owned; students never touch it, which is why their PRs
cannot conflict. Edit team names, taglines and accents to match your roster:

```yaml
teams:
  - name: Team Falcon
    tagline: Fast feedback, small pull requests
    accent: "#7c5cff"
```

Shipped teams are Team Falcon (`#7c5cff`), Team Kestrel (`#00b6a4`), Team Osprey
(`#ff7a45`) and Team Harrier (`#3b82f6`). A bio's `team` must match one of these
names (case-insensitively), so if you rename a team, rename it *before* the
roster CSV goes out — and re-run `python -m generator validate` afterwards,
since existing bios will fail against a renamed team.

Also update `title`, `tagline`, `course` and `footer` for the term.

## 7. Seed one worked example

Merge one real bio through the full workflow yourself — issue, branch, PR,
self-approve with admin bypass, squash merge — before class. It proves the whole
pipeline end to end and means the site is never empty when students first load
it.

## Verification

- [ ] `gh repo view KhourySpecialProjects/linear-github-practice --json defaultBranchRef` reports `testing`
- [ ] A test PR into `testing` cannot merge without 1 approval and both checks
- [ ] `validate-bios` fails on a deliberately broken bio and annotates the file
- [ ] Pushing to `testing` triggers a Coolify deploy and `<deployed-url>` serves the site
- [ ] A test branch named `lgh-1-...` moves its Linear issue automatically
- [ ] Every student can see the repo and has accepted their invitation
- [ ] `python scripts/roster.py roster.csv --ring` output matches the issues you created

## Notes

- Do not create `main`. An accidental `main` becomes the default branch and
  silently breaks the protection rule and the Coolify webhook.
- The bio loader ignores `bios/TEMPLATE.md` and `bios/README.md`, so those two
  files never render — you can document freely in them.
- Rerunning the exercise next term: delete the student bios from `bios/` in one
  instructor PR, keep everything else, re-run `scripts/roster.py` with the new
  roster.
