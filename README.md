# AjsAgyTools

> **Native Google Antigravity (AGY) Tools, Skills, Plugins, and Safety Guardrails**

`AjsAgyTools` brings modern software development standards, safety guardrails, automated handovers, and structured developer skills natively to **Google Antigravity**.

---

## Key Features

1. **Read-Only Auto-Approval Engine (`PreToolUse`):**
   - Safe inspection commands (`git status`, `git diff`, `dir`, `ls`, `cat`, `where.exe`, `python --version`, etc.) are auto-approved (`decision: "allow"`).
   - Autonomous background subagents research uninterrupted without timing out on user permission prompts.
2. **Destructive Command Gating:**
   - Permanent gating (`decision: "ask"` / `"deny"`) for destructive operations:
     - Forced git operations (`git push --force`, `git reset --hard`)
     - Recursive deletion (`rm -rf`, `del /f /q`, `Remove-Item -Recurse -Force`)
     - Hidden processes (`-WindowStyle Hidden`, `Start-Process`, detached jobs)
     - Forced process termination (`kill -9`, `taskkill /f`, `Stop-Process`)
3. **16 Curated Matt Pocock Skills:**
   - Pre-installed under `.agents/skills/`:
     - **Engineering & Testing:** `tdd`, `diagnosing-bugs`, `code-review`, `codebase-design`, `domain-modeling`, `implement`, `improve-codebase-architecture`, `resolving-merge-conflicts`
     - **Planning & Spec:** `to-spec`, `to-tickets`, `grill-me`, `grilling`, `handoff`, `wait-what`, `writing-for-agents`, `ask-matt`
4. **Zero Third-Party Pip Dependencies:**
   - Built entirely on standard Python 3.8+ libraries. Runs out of the box on Windows (`run.cmd`), macOS, and Linux (`run.sh`).

---

## Directory Layout

```text
AjsAgyTools/
├── .agents/                        # Workspace-level AGY configuration
│   ├── rules/                      # Workspace house rules
│   ├── skills/                     # 16 Curated Matt Pocock skills
│   ├── plugins.json                # Plugin discovery entries
│   ├── skills.json                 # Skill discovery roots
│   └── hooks.json                  # Workspace hook definitions
├── plugins/
│   └── agy-house-rules/            # Standalone, distributable Antigravity plugin
│       ├── plugin.json             # Manifest
│       ├── hooks.json              # Hook event declarations
│       ├── rules/                  # House rules & coding standards
│       ├── scripts/                # hook.py, run.cmd, run.sh
│       ├── skills/                 # Plugin-bundled skills (project-docs)
│       └── templates/              # step-card.html template
├── docs/                           # Architecture and agent workflows
├── tests/                          # Automated unittest test suites
├── AGENTS.md                       # Agent instructions
├── GEMINI.md                       # Mirror of AGENTS.md
├── skills-lock.json                # Skill hash verification
├── LICENSE                         # MIT License
└── README.md                       # This document
```

---

## Running Tests

Run the test suite using Python's built-in `unittest` runner:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
```

---

## License

MIT © Ajw2003
