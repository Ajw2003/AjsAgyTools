import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "agy-house-rules", "scripts")))
import hook

class TestRegexSafety(unittest.TestCase):

    def test_hidden_powershell_window_banned(self):
        cmd = "powershell -WindowStyle Hidden -Command calc.exe"
        payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": cmd}}}
        res = hook.handle_pre_tool_use(payload)
        self.assertEqual(res.get("decision"), "ask")

    def test_start_process_banned(self):
        cmd = "Start-Process -FilePath node -ArgumentList 'server.js'"
        payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": cmd}}}
        res = hook.handle_pre_tool_use(payload)
        self.assertEqual(res.get("decision"), "ask")

    def test_safe_diagnostics_allowed(self):
        safe = [
            "ripgrep pattern .",
            "rg foo",
            "findstr /s /i pattern *.*",
            "which git",
            "type README.md",
            "head -n 20 file.txt",
            "cargo test",
            "dotnet test",
            "git branch -a",
            "git tag -l"
        ]
        for cmd in safe:
            with self.subTest(cmd=cmd):
                payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": cmd}}}
                res = hook.handle_pre_tool_use(payload)
                self.assertEqual(res.get("decision"), "allow", f"Failed to allow: {cmd}")

    def test_unknown_command_requires_confirmation(self):
        cmd = "custom_tool --flag"
        payload = {"toolCall": {"name": "run_command", "args": {"CommandLine": cmd}}}
        res = hook.handle_pre_tool_use(payload)
        self.assertEqual(res.get("decision"), "ask")

if __name__ == "__main__":
    unittest.main()
