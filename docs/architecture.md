# Technical Architecture & Lifecycle Engine

## Overview

`Ajw2003/AjsAgyTools` provides a native Antigravity lifecycle engine in `plugins/agy-house-rules/scripts/hook.py`.

## Lifecycle Hooks

1. **`PreToolUse` (Matcher: `run_command`)**:
   - Single-Use Outdated Warning Gate: Checks and immediately consumes session-scoped outdated marker (`agy-house-rules-outdated-{id}.json`). If present, forces `decision: "ask"` once before returning to normal operation.
   - Inspects `CommandLine` using deterministic priority regex matching.
   - Destructive / Risky Patterns: Emits `decision: "ask"` or `decision: "deny"`.
   - Safe Read-Only Patterns: Emits `decision: "allow"`.
   - Background subagents run uninterrupted when inspecting files, checking git status, or reading directories.

2. **`PostToolUse` (Matcher: `write_to_file|replace_file_content`)**:
   - Inspects file modifications.
   - Harvests inline TODOs/FIXMEs and logs them to `.gemini/antigravity/comment_harvest.jsonl`.
   - Emits `{}`.

3. **`PreInvocation`**:
   - Executes three-way version check ($V_{\text{installed}}$, $V_{\text{market}}$, $V_{\text{github}}$) on turn start (`invocationNum == 1`).
   - If outdated, creates atomic session-scoped marker in the system temp directory and prepends loud warning banner to `ephemeralMessage`.
   - Injects active house rules on turn start via `ephemeralMessage`.

4. **`Stop`**:
   - Generates handover summary cards from `templates/step-card.html` to `artifactDirectoryPath/handover_summary.html`.
   - Emits `decision: "allow"`.

## Three-Way Version Check & Outdated Gate (`versioncheck`)

The versioncheck subsystem provides deterministic detection of stale plugin installations across three environments:
1. **Installed Plugin ($V_{\text{installed}}$)**: Parsed from `plugins/agy-house-rules/plugin.json`.
2. **Local Marketplace Cache ($V_{\text{market}}$)**: Looked up from `~/.gemini/config/plugins/agy-house-rules/plugin.json` or `~/.gemini/antigravity/plugins/agy-house-rules/plugin.json`.
3. **Remote Upstream ($V_{\text{github}}$)**: Fetched from GitHub's `main` branch via HTTPS (standard library `urllib.request`) with a strict 3.0-second timeout.

### Triangulation Matrix
- $V_{\text{installed}} \neq V_{\text{market}}$: Installed copy lags behind local marketplace clone (`git pull origin main`).
- $V_{\text{market}} \neq V_{\text{github}}$: Local marketplace clone lags behind GitHub (`git -C ~/.gemini/config/plugins/agy-house-rules pull origin main`, then `git pull origin main`).
- No $V_{\text{market}}$ and $V_{\text{installed}} \neq V_{\text{github}}$: Installed copy lags GitHub directly.

### Dual-Signal Alerting & Marker Lifecycle
- **Signal 1 (Banner)**: Prepended to `ephemeralMessage` on `PreInvocation` (invocation 1).
- **Signal 2 (Single-Use Gate)**: An atomic temporary file (`agy-house-rules-outdated-{safe_id}.json`) is written at `PreInvocation`. On the very first `run_command` in `PreToolUse`, the file is read and immediately unlinked, issuing a one-time interactive confirmation (`decision: "ask"`). Subsequent tool calls are evaluated normally.

### Test Seams & Environment Controls
- `HOUSE_RULES_VERSION_CHECK` / `AGY_HOUSE_RULES_VERSION_CHECK`: Set to `"off"`, `"0"`, `"false"`, or `"no"` to disable version checking entirely.
- `HOUSE_RULES_VC_MARKETPLACE` / `AGY_HOUSE_RULES_VC_MARKETPLACE`: Overrides detected marketplace cache version.
- `HOUSE_RULES_VC_GITHUB` / `AGY_HOUSE_RULES_VC_GITHUB`: Overrides remote upstream version and bypasses HTTP fetch.
- `HOUSE_RULES_VC_GITHUB_URL` / `AGY_HOUSE_RULES_VC_GITHUB_URL`: Overrides target GitHub raw content URL.
