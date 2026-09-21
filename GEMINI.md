# Agent Instructions for AjsAgyTools

Welcome to **AjsAgyTools** (`Ajw2003/AjsAgyTools`), the native tools, skills, and house-rules repository for Google Antigravity (AGY).

## Primary Mandates

1. **Autonomous Read-Only Execution:**
   - Safe inspection commands (`git status`, `git diff`, `dir`, `ls`, `cat`, `where.exe`, etc.) are auto-approved. Background subagents should run uninterrupted.
2. **Destructive Command Gating:**
   - Never run destructive commands without user confirmation:
     - Forced git operations (`git push --force`, `git reset --hard`)
     - Recursive deletion (`rm -rf`, `del /f /q`, `Remove-Item -Recurse -Force`)
     - Process termination (`kill -9`, `taskkill /f`, `Stop-Process`)
3. **Strict Test-Driven Development:**
   - Write unit tests first before implementing or altering functionality.
   - Run tests via `python -m unittest discover -s tests -p "test_*.py" -v`.
4. **Skills Integration:**
   - 16 curated engineering workflows by Matt Pocock are installed under `.agents/skills/`.
   - Call skills as needed: `tdd`, `code-review`, `diagnosing-bugs`, `codebase-design`, `domain-modeling`, `implement`, `improve-codebase-architecture`, `to-spec`, `to-tickets`, `grill-me`, `grilling`, `handoff`, `wait-what`, `writing-for-agents`, `ask-matt`.
5. **Verified Handover:**
   - On completion, produce a handover summary artifact using `templates/step-card.html`.
