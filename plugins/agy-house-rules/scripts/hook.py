#!/usr/bin/env python3
"""
Antigravity House Rules Lifecycle Hook Engine
Ajw2003/AjsAgyTools - Standard-library-only lifecycle engine.
"""

import sys
import json
import re
import os
import pathlib

# ==============================================================================
# 1. Regex Patterns
# ==============================================================================

# Priority 1: Destructive / Risky Commands (never auto-approved)
DESTRUCTIVE_COMMAND_PATTERNS = [
    # Group R1: Backgrounding & Process Hiding (Banned)
    (r"-WindowStyle\s+Hidden", "Hidden PowerShell window execution"),
    (r"Start-Process", "Unsupervised child process spawning (Start-Process)"),
    (r"Start-Job|\s-AsJob", "Detached PowerShell background job"),
    (r"(^|[^0-9A-Za-z_.-])(nohup|setsid|disown)([^0-9A-Za-z_-]|$)", "Process disowning / session detaching"),
    (r"[^&]&\s*$", "Backgrounding with trailing ampersand"),

    # Group R2: Git History Destruction & Remote Force Operations
    (r"git\s+.*push\b.*(--force|--force-with-lease|(^|\s)-f([^0-9A-Za-z-]|$))", "Force pushing to git remote"),
    (r"git\s+.*(reset|revert|clean\s+-fd?|rebase|merge|filter-branch|cherry-pick|am|apply)([^0-9A-Za-z-]|$)", "Git history rewrite or unstaged modification discard"),

    # Group R3: Filesystem & Process Destruction
    (r"(^|[^0-9A-Za-z_./-])rm\s+-[^\s]*[rf]", "Recursive/forced Unix file removal (rm -rf)"),
    (r"Remove-Item\b.*(-Recurse|-Force)", "Recursive/forced PowerShell file removal"),
    (r"(del|erase)\s+/[fqs]|rmdir\s+/s", "Windows command prompt forced/recursive deletion"),
    (r"Stop-Process|taskkill|pkill|kill\s+-9", "Forced process termination"),
    (r"Clear-Content|truncate\s+-s", "File truncation or clearing"),
    (r"git\s+.*(checkout\s+(--|\.(\s|$))|restore([^0-9A-Za-z-]|$))", "Discarding uncommitted working tree modifications"),
    (r"git\s+.*stash\s+(drop|clear)([^0-9A-Za-z-]|$)", "Permanent deletion of stashed changes"),
]

# Priority 2: Safe Read-Only Auto-Approval
READONLY_COMMAND_PATTERNS = [
    # 1. Directory and File Inspection (including piped formatters/filters)
    r"^(dir|ls|Get-ChildItem|gci)(\s+.*)?$",
    r"^(cat|type|Get-Content|gc|head|tail|more|less)(\s+.*)?$",
    r"^(Get-Item|Test-Path|Resolve-Path|gi)(\s+.*)?$",
    r"^(Get-Location|pwd|gl)(\s+.*)?$",
    r"^(find|findstr|grep|rg|ripgrep|awk|sed\s+-n|Select-String|sls)(\s+.*)?$",
    r"^(where\.exe|where|which|Get-Command|gcm)(\s+.*)?$",
    r"^(file|stat|wc|Measure-Object|measure)(\s+.*)?$",
    r"^(Get-Process|gps|ps)(\s+.*)?$",
    r"^(Get-Help|man)(\s+.*)?$",

    # 2. Read-Only Git & GitHub Inspection
    r"^git\s+(status|diff|log|show|branch|tag|rev-parse|describe|remote(\s+-v)?|config\s+--get)(\s+.*)?$",
    r"^gh\s+(repo|issue|pr|release|run|workflow)\s+(list|view|status)(\s+.*)?$",

    # 3. Environment & Runtime Diagnostics
    r"^(python|python3|py)\s+(--version|-V|-c\s+['\"][^'\"]*['\"])$",
    r"^(node|npm|npx|pnpm|yarn|bun)\s+(--version|-v)$",
    r"^(dotnet|cargo|go|rustc)\s+(--version|-v)$",
    r"^(echo|printenv|env|set|Write-Output|Write-Host)(\s+.*)?$",

    # 4. Safe Non-Mutating Testing & Linting (Read-Only Mode)
    r"^(pytest|npm\s+test|cargo\s+test|dotnet\s+test)(\s+.*)?$",
    r"^(python\s+-m\s+unittest|python\s+tests/.*)(\s+.*)?$",
]

# ==============================================================================
# 2. Helper Functions
# ==============================================================================

def _unwrap_command(cmd: str) -> str:
    """
    Unwraps powershell -Command, pwsh -c, and cmd /c execution wrappers to evaluate the inner command.
    """
    s = cmd.strip()

    # Match powershell / pwsh invocation
    ps_prefix = re.match(r"^(?:powershell|pwsh)(?:\.exe)?\b", s, re.IGNORECASE)
    if ps_prefix:
        rest = s[ps_prefix.end():].strip()
        while rest.startswith("-"):
            m = re.match(r"^-([a-zA-Z0-9_-]+)\s*", rest)
            if not m:
                break
            flag_name = m.group(1).lower()
            rest = rest[m.end():].strip()
            if flag_name in ("c", "command"):
                break
            # If flag has an argument like -ExecutionPolicy Bypass or -File foo.ps1
            if flag_name in ("executionpolicy", "ep", "file", "configuration", "windowstyle"):
                arg_match = re.match(r"^(\S+|['\"][^'\"]*['\"])\s*", rest)
                if arg_match:
                    rest = rest[arg_match.end():].strip()
        if (rest.startswith('"') and rest.endswith('"')) or (rest.startswith("'") and rest.endswith("'")):
            rest = rest[1:-1].strip()
        return rest

    # Match cmd /c
    cmd_match = re.match(r"^cmd(?:\.exe)?\s+/c\s+(.*)$", s, re.IGNORECASE | re.DOTALL)
    if cmd_match:
        inner = cmd_match.group(1).strip()
        if (inner.startswith('"') and inner.endswith('"')) or (inner.startswith("'") and inner.endswith("'")):
            inner = inner[1:-1].strip()
        return inner

    return s

# ==============================================================================
# 3. Event Handlers
# ==============================================================================

def handle_pre_tool_use(payload: dict) -> dict:
    """
    Evaluates PreToolUse for run_command.
    Returns:
      {"decision": "allow"} for verified read-only commands
      {"decision": "ask", "reason": "..."} for destructive or unclassified commands
    """
    tool_call = payload.get("toolCall", {})
    name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    if name != "run_command":
        # Other tools auto-approved by default unless gated
        return {"decision": "allow"}

    cmd = args.get("CommandLine", "").strip()
    if not cmd:
        return {"decision": "allow"}

    unwrapped = _unwrap_command(cmd)

    # Priority 1: Check Destructive / Risky Patterns (both raw and unwrapped)
    for pattern, description in DESTRUCTIVE_COMMAND_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE) or re.search(pattern, unwrapped, re.IGNORECASE):
            return {
                "decision": "ask",
                "reason": f"house-rules: gated risky/destructive command ({description}): '{cmd}'"
            }

    # Priority 2: Check Safe Read-Only Patterns (both raw and unwrapped)
    for pattern in READONLY_COMMAND_PATTERNS:
        if re.match(pattern, cmd, re.IGNORECASE) or re.match(pattern, unwrapped, re.IGNORECASE):
            return {"decision": "allow"}

    # Fallback: Safe gating requiring confirmation
    return {
        "decision": "ask",
        "reason": f"house-rules: command requires user confirmation: '{cmd}'"
    }


def handle_post_tool_use(payload: dict) -> dict:
    """
    Evaluates PostToolUse for file writes/edits.
    Harvests inline TODO/FIXME comments and validates artifacts.
    Returns empty dict satisfying contract.
    """
    try:
        tool_call = payload.get("toolCall", {})
        name = tool_call.get("name", "")
        args = tool_call.get("args", {})
        content = args.get("CodeContent") or args.get("ReplacementContent") or ""
        target_file = args.get("TargetFile", "")

        if content:
            # Harvest TODO / FIXME comments
            matches = re.findall(r"(TODO|FIXME|NOTE|BUG|HACK):?\s*(.+)", content, re.IGNORECASE)
            if matches:
                # In AGY environment, log to audit if directory exists
                home_dir = pathlib.Path.home()
                log_dir = home_dir / ".gemini" / "antigravity"
                if log_dir.exists():
                    log_file = log_dir / "comment_harvest.jsonl"
                    with open(log_file, "a", encoding="utf-8") as f:
                        for match_type, comment_text in matches:
                            entry = {
                                "file": target_file,
                                "type": match_type.upper(),
                                "comment": comment_text.strip(),
                                "stepIdx": payload.get("stepIdx")
                            }
                            f.write(json.dumps(entry) + "\n")
    except Exception as err:
        sys.stderr.write(f"house-rules post_tool_use warning: {err}\n")

    return {}


def handle_pre_invocation(payload: dict) -> dict:
    """
    Evaluates PreInvocation before turn starts.
    Injects house rules message on turn start.
    """
    message = (
        "[House Rules Active]: Strict TDD enforced. "
        "Read-only inspection auto-approved. Destructive commands gated. "
        "Artifacts must be verified."
    )
    return {
        "injectSteps": [
            {
                "ephemeralMessage": message
            }
        ]
    }


def handle_stop(payload: dict) -> dict:
    """
    Evaluates Stop event on model completion.
    Generates handover summary card and allows termination.
    """
    try:
        artifact_dir = payload.get("artifactDirectoryPath")
        if artifact_dir and os.path.isdir(artifact_dir):
            template_path = os.path.join(
                os.path.dirname(__file__), "..", "templates", "step-card.html"
            )
            summary_html = os.path.join(artifact_dir, "handover_summary.html")
            if os.path.exists(template_path) and not os.path.exists(summary_html):
                with open(template_path, "r", encoding="utf-8") as tf:
                    content = tf.read()
                with open(summary_html, "w", encoding="utf-8") as out:
                    out.write(content)
    except Exception as err:
        sys.stderr.write(f"house-rules stop hook warning: {err}\n")

    return {"decision": "allow"}


# ==============================================================================
# 3. CLI Dispatcher
# ==============================================================================

def main():
    event_name = sys.argv[1] if len(sys.argv) > 1 else ""

    try:
        raw_input = sys.stdin.read().strip()
        payload = json.loads(raw_input) if raw_input else {}
    except Exception as err:
        sys.stderr.write(f"house-rules error parsing stdin JSON: {err}\n")
        payload = {}

    if not event_name:
        event_name = payload.get("hookName", "PreToolUse")

    if event_name == "PreToolUse":
        result = handle_pre_tool_use(payload)
    elif event_name == "PostToolUse":
        result = handle_post_tool_use(payload)
    elif event_name == "PreInvocation":
        result = handle_pre_invocation(payload)
    elif event_name == "Stop":
        result = handle_stop(payload)
    else:
        sys.stderr.write(f"house-rules: unknown event name '{event_name}'\n")
        result = {"decision": "allow"}

    sys.stdout.write(json.dumps(result))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
