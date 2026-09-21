# Antigravity House Rules

> Native house rules and safety guardrails for Google Antigravity (AGY) workflows.

---

## Rule 1: Never Hide Work in a Background Window or Silent Process
- Commands that conceal execution (e.g. `-WindowStyle Hidden`, detached jobs, unmonitored background runners) are strictly forbidden.
- All processes and subagents must execute under visible, logged supervision.

## Rule 2: Strict Test-Driven Development (TDD)
- When developing or modifying features, always write failing automated tests first (Red), implement minimal logic to pass (Green), and verify all suites cleanly before finishing.
- Unit tests must be independent, fast, and repeatable.

## Rule 3: Commit Frequently on Owned Branches
- Work on isolated branches (prefixed with `agy/*` or `claude/*`). Commits to personal feature branches are auto-approved.
- Never commit directly to protected branches (`main`, `master`, `develop`) without explicit user sign-off and pull request verification.

## Rule 4: Never Take Destructive Actions Without Confirmation
- Destructive commands are permanently gated:
  - Recursive file deletion (`rm -rf`, `del /f /q`, `Remove-Item -Recurse -Force`).
  - Git history rewriting (`git push --force`, `git reset --hard`, `git clean -fd`).
  - Hard process termination (`kill -9`, `Stop-Process -Force`, `taskkill /f`).
- The lifecycle hook automatically intercepts these patterns and requests interactive confirmation.

## Rule 5: Nothing Fails Silently
- Every error, missing binary, or permission rejection must be logged clearly to `stderr` or reported directly to the user.
- Agents must never catch and swallow fatal exceptions or pretend a failed operation succeeded.

## Rule 6: Verify All Generated Artifacts Before Completion
- Never declare a task complete until code compiles, passes tests, and artifacts are verified in the target environment.
- Provide structured handover summaries using the step card standard.
