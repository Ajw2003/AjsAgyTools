# Issue Tracker: GitHub

Issues and specs for `Ajw2003/AjsAgyTools` live as GitHub issues. Use the `gh` CLI for all operations.

## Branch Conventions

- Branch from `main`.
- Owned feature branches follow: `agy/<issue-id>-<slug>` (e.g. `agy/42-read-only-approval`).
- Commits on owned branches are auto-approved. Commits or pushes to `main` require user review.

## Commands

- **Create an issue**: `gh issue create --title "..." --body "..."`
- **Read an issue**: `gh issue view <number> --comments`
- **List issues**: `gh issue list --state open`
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Close an issue**: `gh issue close <number> --comment "..."`
