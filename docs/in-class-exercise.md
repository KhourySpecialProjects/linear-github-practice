# In-Class Exercise Runbook

A 50-minute exercise for 12–20 students. Each student adds one bio file, opens a
pull request into `testing`, gets one peer approval, merges, and watches the
deployed site rebuild.

One-time repository, Linear and deployment setup lives in
[instructor-setup.md](./instructor-setup.md), including the table of
course-specific values (`<org>/<repo>`, `<KEY>`, `<deployed-url>`) this page
refers to. This page is the class-day runbook.

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

None of this is exotic; it is the loop the client work runs on. The exercise
exists to make students execute it once, on a change small enough that the
workflow is the only thing they have to think about.

## Pre-class checklist

- [ ] **Student walkthrough read once, by you.**
      [student-quickstart.md](./student-quickstart.md) is the page students
      follow end to end. Read it as though you were a student and confirm it
      matches how your course actually works — the branch prefix, the review
      ring, the local preview command. It is the only instruction they need,
      so anything stale in it costs class time.
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
- [ ] **Linear issues created** in team `<KEY>`, one per student, titled
      `Add bio for <Full Name>`, in **Todo**, with the generated description
      pasted in — it names the student's file, their team, and their assigned
      reviewer's name and GitHub handle. A fresh team starts empty, so this is
      real work, not a check: budget a few minutes per class of 20.
- [ ] **Students assigned** to their own issues, or told to self-assign at the
      start of class.
- [ ] **GitHub repo** `<org>/<repo>` exists with
      `testing` as the default branch, protected: require a pull request,
      require 1 approving review, require the `validate-bios` and `build-site`
      checks, squash-merge only, auto-delete merged branches, admins can bypass.
- [ ] **Every student has write access** to the repo (via the students' GitHub
      team) and has accepted the invitation *before* class.
- [ ] **Deployment tracking `testing`** with auto-deploy on and
      `<deployed-url>` reachable. Load it once yourself.
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
| 0–5 | **Framing and demo.** One issue -> one branch -> one PR -> review -> merge -> deploy. Show the deployed site and the merged example bio. Say once that this repo has exactly one long-lived branch, `testing`, so nobody hunts for a `main`. |
| 5–10 | **Claim issue, cut branch.** Assign the issue, **Copy git branch name**, `git switch testing && git pull`, `git switch -c abc-##-...` (the prefix is your Linear team key and the issue number — paste what Linear gave you rather than typing it), `git push -u origin HEAD`. Everyone confirms their issue flipped to In Progress. |
| 10–25 | **Write and preview the bio.** `cp bios/TEMPLATE.yml bios/firstname-lastname.yml`, set `name`/`team`/`headline`, replace the `about` block, uncomment any optional fields, then `docker compose up --build` (or `python -m generator validate` for the impatient). Nothing needs deleting to make the template parse. Circulate: most errors are the filename/`name` mismatch and YAML indentation. |
| 25–32 | **Commit, push, open the PR.** One file, imperative message, base `testing`. Watch the checks start. Tell everyone to request the reviewer named on their issue, then stop touching their own PR. |
| 32–42 | **Review ring.** Each student reviews exactly one PR: `name`, `team`, `headline` and `about` present and valid, filename matches the name and ends in `.yml`, `about` reads professionally, no other files touched. Approve when good enough. Call out the two-minute mark so nobody sits on a review. |
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
| CI red at minute 45 | Two options: read the annotation with them and fix it in 30 seconds, or admin-bypass the merge and have them fix it in a follow-up PR. Bypassing on purpose, out loud, is a better lesson than a stalled room — and it does not break the site, because `build` is not strict (see below). |
| A bypassed bio is degraded on the deployed site | Expected, not broken. The bio renders with fallback values: under **Unassigned** if the `team` is wrong or missing, with `Bio still needs a headline` or a placeholder `about` if those could not be read. The deploy log carries the warning. The fix is the student's follow-up PR. |
| CI red for everyone at once | Something is wrong with the repo, not the students: check `site.yml` parses and the last merge to `testing` is green. Fall back to local `python -m generator validate` as the gate and merge with admin bypass. |
| Student finishes early | Have them review a second PR (a real review, not a rubber stamp), or improve their `about` copy and push an update so they exercise re-request review. |
| YAML indentation wave | A tab in the indentation gives `indented with a tab - YAML only allows spaces, so replace tabs with two spaces`; an unquoted value containing `': '` gives `invalid YAML at line N: mapping values are not allowed here - a value containing ': ' must be wrapped in quotes`. Demo both fixes once for the whole room: spaces only, and quote the value. |
| Bio silently missing from the site | They saved `firstname-lastname.yaml`. The loader reads `*.y*ml`, so it reports `filename must be lowercase 'firstname-lastname.yml' (letters, digits and hyphens only)` instead of ignoring it — have them rename to `.yml`. |
| Merge conflict | Should be impossible — one new file per student. It means they edited someone else's bio, `site.yml`, or a repo file. Have them revert that file and re-push. |
| Docker will not start | Send them down the no-Docker path: `python3 -m venv .venv`, `pip install -r requirements.txt`, `python -m generator serve` on http://localhost:8000. |
| Linear issue did not move | The issue ID is missing from the branch name. Rename the branch from Linear's copied name and re-push. |
| Deploy does not appear | Check the deployment log on the projector — a slow deploy is a teaching moment, not a failure. |

## When you bypass a straggler at minute 45

Merging a red pull request with admin bypass does not take the site down. Know
exactly why, so you can say it out loud instead of guessing.

The merge to `testing` fires the deploy webhook like any other merge, and the
image build runs `python -m generator build` — deliberately **not**
`--strict`. The bad file is repaired with fallback values, every other card is
unaffected, and the build exits 0 after printing a warning. The deploy log
shows it:

```
warning: 1 problem(s) in bios/; 1 bio(s) rendered with fallback values:
  bios/jane-doe.yml: team 'Team Flacon' is not one of the course teams - use one of: Team Falcon, Team Kestrel, Team Osprey, Team Harrier, Team Merlin, Team Goshawk, Team Kite, Team Caracara, Team Peregrine, Team Condor, Team Eagle
The site was built anyway. Run 'python -m generator validate' to treat these as failures, which is what CI does on every pull request.
```

Then the usual `Built N page(s) for M bio(s) into /dist/` line. That warning is
how you spot a degraded bio after class: grep the deploy log for `warning:`.

On the site itself the card is visibly degraded rather than missing. A wrong or
missing `team` groups it under a trailing **Unassigned** heading after the real
teams; a missing `headline` reads `Bio still needs a headline`; an `about` that
could not be read reads as a placeholder pointing at the validator.

The fix is a follow-up PR from that student. It is gated by `validate-bios`
like every other PR, so it cannot merge until the file is right, and the next
deploy moves the card into its real team. Put the degraded card on the
projector while you are there — the site survived, the mistake is visible, and
it is still somebody's job — then make sure the follow-up PR actually lands
before the room empties.

## Debrief (minutes 48–50)

Three points, out loud:

1. **What just happened is the whole loop.** Issue, branch, PR, review, merge,
   automatic deploy. On client projects the diff is bigger and the review is
   longer; the loop is identical.
2. **`testing` was protected, and that is why the loop exists.** Nobody pushed
   to a deployed branch. Every change on the live site arrived through a
   reviewed, merged pull request.
3. **You did one hop of a longer path.** This repo has exactly one deployed
   branch on purpose, so the exercise fits in 50 minutes. A real project
   usually has several deployed environments in a line, and a change is merged
   forward one step at a time, each merge deploying its own environment. The
   pull request you just merged would be promoted again, more than once, with
   somebody's approval each time — which is why "merge to a protected branch"
   is a decision and not a keystroke.

Ask two questions before they leave: who had a red check and what did it say,
and what did you look at when you reviewed someone else's PR.

## After class

- [ ] Confirm every issue in team `<KEY>` is **Done**; chase the ones that are not.
- [ ] Merge or close any leftover PRs; delete stale branches.
- [ ] Confirm the deployed site lists everyone.
- [ ] Confirm nothing is left under **Unassigned** and the last deploy log has
      no `warning:` line; if it does, chase that student's follow-up PR. Locally:
      `python -m generator validate`.
- [ ] Note the timings that slipped, and adjust the pre-class Docker check.
