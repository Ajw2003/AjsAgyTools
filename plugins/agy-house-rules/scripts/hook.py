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
import tempfile
import urllib.request
from typing import Optional, Tuple, List, Dict

# ==============================================================================
# Version Check Configuration & Constants
# ==============================================================================
_GITHUB_PLUGIN_JSON_URL = (
    "https://raw.githubusercontent.com/Ajw2003/AjsAgyTools/main/"
    "plugins/agy-house-rules/plugin.json"
)
_GITHUB_FETCH_TIMEOUT = 3.0
_TRACE_OFF = {"off", "0", "false", "no"}

_VC_UPDATE_CMD = "git pull origin main"
_VC_MARKETPLACE_CMD = "git -C ~/.gemini/config/plugins/agy-house-rules pull origin main"

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


def _version_check_enabled() -> bool:
    val = os.environ.get("AGY_HOUSE_RULES_VERSION_CHECK")
    if val is None:
        val = os.environ.get("HOUSE_RULES_VERSION_CHECK", "on")
    return val.strip().lower() not in _TRACE_OFF


def _installed_version(problems: Optional[List[str]] = None) -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.normpath(os.path.join(here, "..", "plugin.json"))
    version = ""
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                version = data.get("version", "") or ""
    except Exception as exc:
        if problems is not None:
            problems.append(f"could not read installed plugin.json ({type(exc).__name__})")
    return version


def _marketplace_version(problems: Optional[List[str]] = None) -> str:
    override = os.environ.get("AGY_HOUSE_RULES_VC_MARKETPLACE") or os.environ.get("HOUSE_RULES_VC_MARKETPLACE")
    if override is not None:
        return override
    home = os.path.expanduser("~")
    candidate_paths = [
        os.path.join(home, ".gemini", "config", "plugins", "agy-house-rules", "plugin.json"),
        os.path.join(home, ".gemini", "antigravity", "plugins", "agy-house-rules", "plugin.json"),
    ]
    for path in candidate_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    ver = data.get("version", "")
                    if ver:
                        return ver
            except Exception as exc:
                if problems is not None:
                    problems.append(f"could not read marketplace plugin.json at {path} ({type(exc).__name__})")
    return ""


def _github_version(problems: Optional[List[str]] = None) -> str:
    override = os.environ.get("AGY_HOUSE_RULES_VC_GITHUB") or os.environ.get("HOUSE_RULES_VC_GITHUB")
    if override is not None:
        return override
    url = (
        os.environ.get("AGY_HOUSE_RULES_VC_GITHUB_URL")
        or os.environ.get("HOUSE_RULES_VC_GITHUB_URL")
        or _GITHUB_PLUGIN_JSON_URL
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "agy-house-rules-versioncheck"})
        with urllib.request.urlopen(req, timeout=_GITHUB_FETCH_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        return data.get("version", "") or ""
    except Exception as exc:
        if problems is not None:
            problems.append(f"could not reach remote version endpoint ({type(exc).__name__})")
        return ""


def _resolve_session_id(payload: dict) -> str:
    if not isinstance(payload, dict):
        return ""
    sid = payload.get("conversationId") or payload.get("sessionId") or payload.get("session_id") or ""
    return str(sid).strip()


def _outdated_marker_path(session_id: str) -> str:
    if not session_id:
        return ""
    safe = re.sub(r"[^0-9A-Za-z_-]", "_", session_id)[:100]
    return os.path.join(tempfile.gettempdir(), f"agy-house-rules-outdated-{safe}.json")


def _write_outdated_marker(session_id: str, reasons: list) -> None:
    path = _outdated_marker_path(session_id)
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"reasons": reasons}, f)
    except OSError as exc:
        sys.stderr.write(f"house-rules versioncheck: could not write session marker: {exc}\n")


def _read_and_clear_outdated_marker(session_id: str) -> Optional[dict]:
    path = _outdated_marker_path(session_id)
    if not path or not os.path.isfile(path):
        return None
    data = None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = None
    try:
        os.remove(path)
    except OSError as exc:
        sys.stderr.write(f"house-rules guard: could not remove marker {path}: {exc}\n")
    return data


def _check_version_freshness(session_id: str = "") -> Tuple[List[str], str]:
    if not _version_check_enabled():
        return [], ""

    problems = []
    installed = _installed_version(problems)
    market_version = _marketplace_version(problems)
    github_version = _github_version(problems)

    reasons = []

    # Case 1: Installed lags local marketplace cache
    if installed and market_version and installed != market_version:
        reasons.append(
            f"installed copy is {installed} but the local marketplace clone has {market_version} - run `{_VC_UPDATE_CMD}`."
        )

    # Case 2: Local marketplace cache lags GitHub
    if market_version and github_version and market_version != github_version:
        reasons.append(
            f"the local marketplace clone is {market_version} but GitHub's default branch has {github_version} - "
            f"the marketplace clone itself has not synced. Run `{_VC_MARKETPLACE_CMD}`, then `{_VC_UPDATE_CMD}`."
        )

    # Case 3: No local marketplace cache, installed directly lags GitHub
    elif not market_version and installed and github_version and installed != github_version:
        reasons.append(
            f"installed copy is {installed} but GitHub's default branch has {github_version} "
            f"(the local marketplace clone could not be checked). Run `{_VC_MARKETPLACE_CMD}`, then `{_VC_UPDATE_CMD}`."
        )

    banner = ""
    if reasons:
        if session_id:
            _write_outdated_marker(session_id, reasons)

        banner_lines = [
            "=" * 70,
            "AGY-HOUSE-RULES PLUGIN IS OUT OF DATE",
            "=" * 70,
            "",
            "Before doing any other work this session: tell the user plainly that this",
            "session is running an out-of-date copy of the agy-house-rules plugin, and ask",
            "for permission to update it yourself, right now, on this machine.",
            "Then stop and wait for the user's answer. Reporting the problem and continuing",
            "into unrelated work in the same turn is not permitted.",
            "",
            "If they say yes: run the update command(s) below in order:",
        ]
        for r in reasons:
            banner_lines.append(f"  - {r}")
        banner_lines.extend([
            "",
            "As a second, harness-enforced signal in case this context is missed, the",
            "first shell command run this session will also carry a permission prompt",
            "repeating this notice, once.",
            "=" * 70,
        ])
        banner = "\n".join(banner_lines)

    return reasons, banner


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

    # Consume-once outdated marker check
    session_id = _resolve_session_id(payload)
    outdated = _read_and_clear_outdated_marker(session_id)
    if outdated and outdated.get("reasons"):
        lines = [
            "house-rules: AGY-HOUSE-RULES PLUGIN IS OUT OF DATE",
            "",
            "  Notice detected at invocation start (found at session start, not by this command):"
        ]
        for r in outdated["reasons"]:
            lines.append(f"    - {r}")
        lines.extend([
            "",
            f"  Pending command: '{cmd}'",
            "",
            "Approve to execute the pending command anyway, or reject to update the plugin first."
        ])
        return {
            "decision": "ask",
            "reason": "\n".join(lines)
        }

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
    Runs three-way version check and injects house rules / update banner.
    """
    base_house_rules = (
        "[House Rules Active]: Strict TDD enforced. "
        "Read-only inspection auto-approved. Destructive commands gated. "
        "Artifacts must be verified."
    )

    inv_num = payload.get("invocationNum", 1)
    session_id = _resolve_session_id(payload)

    reasons = []
    banner = ""
    if inv_num == 1:
        reasons, banner = _check_version_freshness(session_id)

    if banner:
        ephemeral_message = f"{banner}\n\n{base_house_rules}"
    else:
        ephemeral_message = base_house_rules

    return {
        "injectSteps": [
            {
                "ephemeralMessage": ephemeral_message
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
