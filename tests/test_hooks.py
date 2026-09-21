import io
import json
import unittest
import sys
import os
import tempfile

# Ensure hook module can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "agy-house-rules", "scripts")))
import hook

class TestAgyHooks(unittest.TestCase):

    def test_pre_tool_use_readonly_auto_approval(self):
        """Verify read-only inspection commands receive decision: 'allow'."""
        readonly_commands = [
            "git status",
            "git diff HEAD~1",
            "git log -n 5 --oneline",
            "dir",
            "ls -la",
            "cat package.json",
            "where.exe python",
            "where py",
            "Get-ChildItem -Path .",
            "python --version",
            "pytest tests/",
            "npm test"
        ]
        for cmd in readonly_commands:
            with self.subTest(command=cmd):
                payload = {
                    "toolCall": {"name": "run_command", "args": {"CommandLine": cmd}},
                    "conversationId": "test-uuid"
                }
                result = hook.handle_pre_tool_use(payload)
                self.assertEqual(result.get("decision"), "allow", f"Failed to auto-approve: {cmd}")

    def test_pre_tool_use_destructive_commands_gated(self):
        """Verify destructive commands receive decision: 'ask' or 'deny'."""
        destructive_commands = [
            "rm -rf /",
            "rm -rf node_modules",
            "del /f /q *.*",
            "rmdir /s /q temp",
            "Remove-Item -Recurse -Force .",
            "git push --force origin main",
            "git push -f origin main",
            "git reset --hard HEAD~1",
            "git clean -fd",
            "kill -9 1234",
            "taskkill /f /im node.exe",
            "Stop-Process -Name code -Force"
        ]
        for cmd in destructive_commands:
            with self.subTest(command=cmd):
                payload = {
                    "toolCall": {"name": "run_command", "args": {"CommandLine": cmd}},
                    "conversationId": "test-uuid"
                }
                result = hook.handle_pre_tool_use(payload)
                self.assertIn(result.get("decision"), ["ask", "deny"], f"Failed to gate: {cmd}")
                self.assertTrue(len(result.get("reason", "")) > 0)

    def test_pre_invocation_inject_steps(self):
        """Verify PreInvocation injects ephemeral house rules message."""
        payload = {"invocationNum": 1, "conversationId": "test-uuid"}
        result = hook.handle_pre_invocation(payload)
        self.assertIn("injectSteps", result)
        self.assertTrue(len(result["injectSteps"]) > 0)
        self.assertIn("ephemeralMessage", result["injectSteps"][0])

    def test_post_tool_use_returns_empty_object(self):
        """Verify PostToolUse satisfies contract returning {}."""
        payload = {
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": "test.txt", "CodeContent": "Hello"}
            }
        }
        result = hook.handle_post_tool_use(payload)
        self.assertEqual(result, {})

    def test_stop_returns_allow(self):
        """Verify Stop hook allows termination when requirements are met."""
        payload = {
            "terminationReason": "model_stop",
            "fullyIdle": True,
            "artifactDirectoryPath": tempfile.gettempdir()
        }
        result = hook.handle_stop(payload)
        self.assertEqual(result.get("decision"), "allow")

if __name__ == "__main__":
    unittest.main()
