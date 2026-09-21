# Technical Architecture & Lifecycle Engine

## Overview

`Ajw2003/AjsAgyTools` provides a native Antigravity lifecycle engine in `plugins/agy-house-rules/scripts/hook.py`.

## Lifecycle Hooks

1. **`PreToolUse` (Matcher: `run_command`)**:
   - Inspects `CommandLine` using deterministic priority regex matching.
   - Destructive / Risky Patterns: Emits `decision: "ask"` or `decision: "deny"`.
   - Safe Read-Only Patterns: Emits `decision: "allow"`.
   - Background subagents run uninterrupted when inspecting files, checking git status, or reading directories.

2. **`PostToolUse` (Matcher: `write_to_file|replace_file_content`)**:
   - Inspects file modifications.
   - Harvests inline TODOs/FIXMEs and logs them to `.gemini/antigravity/comment_harvest.jsonl`.
   - Emits `{}`.

3. **`PreInvocation`**:
   - Injects active house rules on turn start via `ephemeralMessage`.

4. **`Stop`**:
   - Generates handover summary cards from `templates/step-card.html` to `artifactDirectoryPath/handover_summary.html`.
   - Emits `decision: "allow"`.
