import os
import tempfile
import unittest
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "plugins", "agy-house-rules", "scripts")))
import hook

class TestVersionCheck(unittest.TestCase):

    def setUp(self):
        self.clean_env = os.environ.copy()
        self.session_id = "test-session-vc-1234"
        # Ensure test isolation
        marker = hook._outdated_marker_path(self.session_id)
        if os.path.isfile(marker):
            os.remove(marker)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.clean_env)
        marker = hook._outdated_marker_path(self.session_id)
        if os.path.isfile(marker):
            os.remove(marker)

    def test_01_clean_matching_versions_no_banner(self):
        """When installed, marketplace, and GitHub versions match, no banner or marker is created."""
        os.environ["HOUSE_RULES_VC_MARKETPLACE"] = "1.0.0"
        os.environ["HOUSE_RULES_VC_GITHUB"] = "1.0.0"
        
        payload = {"conversationId": self.session_id}
        res = hook.handle_pre_invocation(payload)
        
        self.assertNotIn("AGY-HOUSE-RULES PLUGIN IS OUT OF DATE", res["injectSteps"][0]["ephemeralMessage"])
        self.assertFalse(os.path.exists(hook._outdated_marker_path(self.session_id)))

    def test_02_installed_lagging_behind_marketplace(self):
        """When installed is 1.0.0 and marketplace is 1.1.0, banner and marker are created naming git pull."""
        os.environ["HOUSE_RULES_VC_MARKETPLACE"] = "1.1.0"
        os.environ["HOUSE_RULES_VC_GITHUB"] = "1.1.0"
        
        payload = {"conversationId": self.session_id}
        res = hook.handle_pre_invocation(payload)
        
        banner = res["injectSteps"][0]["ephemeralMessage"]
        self.assertIn("AGY-HOUSE-RULES PLUGIN IS OUT OF DATE", banner)
        self.assertIn("installed copy is 1.0.0 but the local marketplace clone has 1.1.0", banner)
        self.assertIn("git pull origin main", banner)
        self.assertTrue(os.path.exists(hook._outdated_marker_path(self.session_id)))

    def test_03_marketplace_lagging_behind_github(self):
        """When marketplace is 1.0.0 and GitHub is 1.2.0, banner warns that marketplace clone has not synced."""
        os.environ["HOUSE_RULES_VC_MARKETPLACE"] = "1.0.0"
        os.environ["HOUSE_RULES_VC_GITHUB"] = "1.2.0"
        
        payload = {"conversationId": self.session_id}
        res = hook.handle_pre_invocation(payload)
        
        banner = res["injectSteps"][0]["ephemeralMessage"]
        self.assertIn("AGY-HOUSE-RULES PLUGIN IS OUT OF DATE", banner)
        self.assertIn("the local marketplace clone is 1.0.0 but GitHub's default branch has 1.2.0", banner)
        self.assertIn("git -C ~/.gemini/config/plugins/agy-house-rules pull origin main", banner)

    def test_04_no_marketplace_installed_lags_github(self):
        """When marketplace is empty/missing, installed lags GitHub directly."""
        os.environ["HOUSE_RULES_VC_MARKETPLACE"] = ""
        os.environ["HOUSE_RULES_VC_GITHUB"] = "2.0.0"
        
        payload = {"conversationId": self.session_id}
        res = hook.handle_pre_invocation(payload)
        
        banner = res["injectSteps"][0]["ephemeralMessage"]
        self.assertIn("AGY-HOUSE-RULES PLUGIN IS OUT OF DATE", banner)
        self.assertIn("installed copy is 1.0.0 but GitHub's default branch has 2.0.0", banner)

    def test_05_network_failure_fails_open(self):
        """When GitHub is unreachable (empty string returned), fail open: no banner or marker if installed matches market."""
        os.environ["HOUSE_RULES_VC_MARKETPLACE"] = "1.0.0"
        os.environ["HOUSE_RULES_VC_GITHUB"] = ""  # Simulates network error / timeout
        
        payload = {"conversationId": self.session_id}
        res = hook.handle_pre_invocation(payload)
        
        self.assertNotIn("AGY-HOUSE-RULES PLUGIN IS OUT OF DATE", res["injectSteps"][0]["ephemeralMessage"])
        self.assertFalse(os.path.exists(hook._outdated_marker_path(self.session_id)))

    def test_06_toggle_disabled(self):
        """When HOUSE_RULES_VERSION_CHECK='off', version check is completely bypassed."""
        os.environ["HOUSE_RULES_VERSION_CHECK"] = "off"
        os.environ["HOUSE_RULES_VC_MARKETPLACE"] = "9.9.9"
        os.environ["HOUSE_RULES_VC_GITHUB"] = "9.9.9"
        
        payload = {"conversationId": self.session_id}
        res = hook.handle_pre_invocation(payload)
        
        self.assertNotIn("AGY-HOUSE-RULES PLUGIN IS OUT OF DATE", res["injectSteps"][0]["ephemeralMessage"])
        self.assertFalse(os.path.exists(hook._outdated_marker_path(self.session_id)))

    def test_07_marker_single_use_consumption_in_pre_tool_use(self):
        """Outdated marker forces decision: 'ask' on the first command, then disappears and auto-approves safe commands."""
        # 1. Simulate PreInvocation creating outdated marker
        os.environ["HOUSE_RULES_VC_MARKETPLACE"] = "1.1.0"
        hook.handle_pre_invocation({"conversationId": self.session_id})
        self.assertTrue(os.path.exists(hook._outdated_marker_path(self.session_id)))

        # 2. First tool call (normally safe 'dir')
        tool_payload = {
            "conversationId": self.session_id,
            "toolCall": {"name": "run_command", "args": {"CommandLine": "dir"}}
        }
        first_call = hook.handle_pre_tool_use(tool_payload)
        self.assertEqual(first_call.get("decision"), "ask")
        self.assertIn("AGY-HOUSE-RULES PLUGIN IS OUT OF DATE", first_call.get("reason", ""))
        self.assertIn("Pending command: 'dir'", first_call.get("reason", ""))

        # 3. Verify marker is deleted
        self.assertFalse(os.path.exists(hook._outdated_marker_path(self.session_id)))

        # 4. Second tool call with same command must be auto-approved
        second_call = hook.handle_pre_tool_use(tool_payload)
        self.assertEqual(second_call.get("decision"), "allow")

    def test_08_session_isolation(self):
        """Marker created for Session A does not affect Session B."""
        hook._write_outdated_marker("session-A", ["Reason A"])
        
        tool_payload_b = {
            "conversationId": "session-B",
            "toolCall": {"name": "run_command", "args": {"CommandLine": "dir"}}
        }
        res_b = hook.handle_pre_tool_use(tool_payload_b)
        self.assertEqual(res_b.get("decision"), "allow")
        
        # Cleanup
        hook._read_and_clear_outdated_marker("session-A")

if __name__ == "__main__":
    unittest.main()
