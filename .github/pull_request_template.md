## What changed

<!-- One line. Example: "Add bio for Jane Doe (Team Falcon)." -->

## Linear issue

<!-- Nothing to paste: the issue links itself from the issue ID in your branch
name (the part Linear's "Copy git branch name" puts in front, like abc-12), and
opening this PR moves it to In Review. If no issue appears, the ID is missing
from your branch name. -->

## Author checklist

- [ ] Exactly one new file, `bios/firstname-lastname.yml`, and nothing else
- [ ] Filename is the slug of my `name` field ("Jane Doe" -> `jane-doe.yml`)
- [ ] Previewed locally (`docker compose up --build`, or `python -m generator serve`)
- [ ] CI is green (`validate-bios`, `build-site`)
- [ ] Requested the reviewer named on my Linear issue
- [ ] Base branch is `testing`

## Reviewer

Check these four things, then Approve or Request changes:

- [ ] Required keys present: `name`, `team`, `headline`, `about`; `team` is one
      of the teams listed in `site.yml`
- [ ] Filename matches the author's name and ends in `.yml`
- [ ] `about` reads professionally — a real sentence or two, no placeholder text
- [ ] No files outside this author's own bio were touched

Be specific and kind, comment on the code and not the person, approve when it
is good enough to ship rather than perfect, and save **Request changes** for a
real blocker.
