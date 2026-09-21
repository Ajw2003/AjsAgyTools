# Domain Docs

How agents should consume this repository's domain documentation and understand its mission.

## Mission & Purpose

`Ajw2003/AjsAgyTools` is the native Antigravity repository containing:
1. **Antigravity House Rules (`plugins/agy-house-rules`)**: A native Antigravity lifecycle plugin that implements:
   - Zero-friction read-only command auto-approval (`decision: "allow"`), ensuring background subagents research uninterrupted without permission prompts.
   - Destructive command gating (`decision: "ask"` / `"deny"`), blocking destructive git history rewrites, unmonitored background tasks, and recursive deletions.
   - Ephemeral coding standards injection on turn start (`PreInvocation`).
   - Audit logging and comment harvesting (`PostToolUse`).
   - Automated handover summary card generation (`Stop`).
2. **Curated Skills Suite (`.agents/skills`)**: 16 engineering, diagnosis, refactoring, and collaboration skills originated by Matt Pocock, ported for Antigravity agents.
3. **Cross-Platform Compatibility**: Standard-library-only Python hook engines (`hook.py`) with native Windows batch (`run.cmd`) and POSIX shell (`run.sh`) launchers.

## Directory Layout Conventions

```
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
└── README.md                       # Documentation & quickstart
```
