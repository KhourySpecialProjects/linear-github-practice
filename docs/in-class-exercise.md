# In-Class Exercise Runbook

A 50-minute exercise for 12–20 students. Each student adds one bio file, opens a
pull request into `testing`, gets one peer approval, merges, and watches the
deployed site rebuild.

One-time repository, Linear and Coolify setup lives in
[instructor-setup.md](./instructor-setup.md). This page is the class-day
runbook.

## Learning objectives

By the end of the session every student has, once, for real:

1. Turned a Linear issue into a branch using **Copy git branch name**, and seen
   Linear move the issue Todo -> In Progress -> In Review -> Done with no manual
   status changes.
2. Branched from an up-to-date protected branch, committed one focused change
   with an imperative message, and pushed.
3. Opened a pull request into `testing`, read a failing CI annotation, and fixed
   it themselves.
4. Reviewed a teammate's pull request and submitted an explicit verdict.
5. Squash-merged an approved, green PR and watched an automatic deploy follow
   the merge.

The rules behind all of this are in
[Developer Expectations](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/developer-expectations.md);
the exercise exists to make students execute them once before the client work
starts.

## Pre-class checklist

- [ ] **Playbooks published.** Every playbook link in this repo points at
      `KhourySpecialProjects/practicum-playbooks` on `main`. As of writing,
      only `README.md`, `blacksmith-setup.md` and `onboarding.md` are on
      `main` — the seven workflow playbooks students need most
      (`start-an-issue`, `working-on-your-branch`, `open-a-pull-request`,
      `reviewing-a-pull-request`, `respond-to-review-and-merge`,
      `developer-expectations`, `environments-and-deployment`) are still
      unpushed local files. Commit, merge to `main`, and confirm students have
      read access, or those links 404 mid-exercise.
- [ ] **Roster CSV** ready: `name,github,team` header, one row per student
      (`roster.example.csv` in the repo root shows the shape).
- [ ] **Issue text and review ring generated**:

      ```sh
      python scripts/roster.py roster.csv            # issue title + description per student
      python scripts/roster.py roster.csv --ring     # the Author/Reviewer ring
      python scripts/roster.py roster.csv --slug-only # expected filenames
      ```

      The ring is the roster sorted by name: student *n* reviews student *n+1*,
      the last reviews the first.
- [ ] **Linear issues created** in team **LGH**, one per student, titled
      `Add bio for <Full Name>`, in **Todo**, with the generated description
      pasted in — it names the student's file, their team, and their assigned
      reviewer's name and GitHub handle. The LGH team starts empty, so this is
      real work, not a check: budget a few minutes per class of 20.
- [ ] **Students assigned** to their own issues, or told to self-assign at the
      start of class.
- [ ] **GitHub repo** `KhourySpecialProjects/linear-github-practice` exists with
      `testing` as the default branch, protected: require a pull request,
      require 1 approving review, require the `validate-bios` and `build-site`
      checks, squash-merge only, auto-delete merged branches, admins can bypass.
- [ ] **Every student has write access** to the repo (via the students' GitHub
      team) and has accepted the invitation *before* class.
- [ ] **Coolify app** tracking `testing` with the Docker Compose build pack
      pointing at `docker-compose.coolify.yml`, auto-deploy on, domain
      reachable. Load it once yourself.
- [ ] **One worked example already merged** — a bio on the deployed site — so
      students see the finished shape and the site is never empty.
- [ ] **Local Docker verified** by each student in advance:
      `docker compose up --build` then http://localhost:8088 (they can override
      a busy port with `SITE_PORT=9090`). Docker pulling base images for the
      first time on classroom wifi is the single biggest time sink; the
      no-Docker path (`python -m generator serve`) is the fallback.
- [ ] **Projector tabs open**: a Linear issue, the repo's Pull requests tab, the
      deployed site.

## Timeline (50 minutes)

| Minutes | What happens |
|---|---|
| 0–5 | **Framing and demo.** One issue -> one branch -> one PR -> review -> merge -> deploy. Show the deployed site and the merged example bio. State the one difference from the playbooks: this repo has only `testing`. |
| 5–10 | **Claim issue, cut branch.** Assign the issue, **Copy git branch name**, `git switch testing && git pull`, `git switch -c lgh-##-...`, `git push -u origin HEAD`. Everyone confirms their issue flipped to In Progress. |
| 10–25 | **Write and preview the bio.** `cp bios/TEMPLATE.md bios/firstname-lastname.md`, delete the comment on line 1, fill the frontmatter, write the body, then `docker compose up --build` (or `python -m generator validate` for the impatient). Circulate: most errors are the filename/`name` mismatch and a missing `---` on line 1. |
| 25–32 | **Commit, push, open the PR.** One file, imperative message, base `testing`. Watch the checks start. Tell everyone to request the reviewer named on their issue, then stop touching their own PR. |
| 32–42 | **Review ring.** Each student reviews exactly one PR: frontmatter valid, filename matches the name, body reads professionally, no other files touched. Approve when good enough. Call out the two-minute mark so nobody sits on a review. |
| 42–48 | **Merge and deploy.** Squash and merge, delete branch, confirm Linear went to Done. Put the deployed site on the projector and refresh as cards appear. |
| 48–50 | **Debrief.** See below. |

Timing note: the write-and-preview block is the flexible one. If the room is
ahead at minute 20, start the PR wave early — the review ring is the part that
must not be rushed, because it is the part they have never done before.

## Failure modes and what you do

| Symptom | Instructor response |
|---|---|
| Student blocked waiting on a reviewer (absent, slow, or stuck on their own bio) | Approve the PR yourself. Nobody waits more than two minutes on the ring. |
| Ring broken by an absent student | Re-point the orphaned author at the next present student in the ring and say so out loud; do not re-generate the ring mid-class. |
| CI red at minute 45 | Two options: read the annotation with them and fix it in 30 seconds, or admin-bypass the merge and have them fix it in a follow-up PR. Bypassing on purpose, out loud, is a better lesson than a stalled room. |
| CI red for everyone at once | Something is wrong with the repo, not the students: check `site.yml` parses and the last merge to `testing` is green. Fall back to local `python -m generator validate` as the gate and merge with admin bypass. |
| Student finishes early | Have them review a second PR (a real review, not a rubber stamp), or improve their body copy and push an update so they exercise re-request review. |
| "No frontmatter found" wave | They left the HTML comment on line 1 of the copied template. Demo the fix once for the whole room. |
| Merge conflict | Should be impossible — one new file per student. It means they edited someone else's bio, `site.yml`, or a repo file. Have them revert that file and re-push. |
| Docker will not start | Send them down the no-Docker path: `python3 -m venv .venv`, `pip install -r requirements.txt`, `python -m generator serve` on http://localhost:8000. |
| Linear issue did not move | The issue ID is missing from the branch name. Rename the branch from Linear's copied name and re-push. |
| Deploy does not appear | Check the Coolify deployment log on the projector — a slow deploy is a teaching moment, not a failure. |

## Debrief (minutes 48–50)

Three points, out loud:

1. **What just happened is the whole loop.** Issue, branch, PR, review, merge,
   automatic deploy. On client projects the diff is bigger and the review is
   longer; the loop is identical.
2. **`testing` was protected, and that is why the loop exists.** Nobody pushed
   to a deployed branch. Every change on the live site arrived through a
   reviewed, merged pull request.
3. **This repo showed you the first environment of four.** Real projects promote
   Local -> Testing -> Staging -> Production, merging forward one step at a
   time, each merge auto-deploying its own environment; see
   [Environments & Deployment](https://github.com/KhourySpecialProjects/practicum-playbooks/blob/main/environments-and-deployment.md).
   Today you did Local -> Testing. On your client project the same PR you just
   merged gets promoted twice more, which is why "merge to a protected branch"
   is a decision and not a keystroke.

Ask two questions before they leave: who had a red check and what did it say,
and what did you look at when you reviewed someone else's PR.

## After class

- [ ] Confirm every issue in LGH is **Done**; chase the ones that are not.
- [ ] Merge or close any leftover PRs; delete stale branches.
- [ ] Confirm the deployed site lists everyone.
- [ ] Note the timings that slipped, and adjust the pre-class Docker check.
