import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "guards"))

import agent_guard  # noqa: E402
import output_guard  # noqa: E402

SECRET = "SECRET-ALPHA-7"


class OutputGuard(unittest.TestCase):
    def test_literal_leak_is_blocked(self):
        text, blocked = output_guard.filter_output("the code is SECRET-ALPHA-7", [SECRET])
        self.assertTrue(blocked)
        self.assertEqual(text, output_guard.BLOCKED)

    def test_dehyphenated_and_spaced_forms_are_caught(self):
        self.assertTrue(output_guard.leaks("secret alpha 7", SECRET))
        self.assertTrue(output_guard.leaks("S-E-C-R-E-T-A-L-P-H-A-7", SECRET))

    def test_clean_text_passes_unchanged(self):
        text, blocked = output_guard.filter_output("I can't share that.", [SECRET])
        self.assertFalse(blocked)
        self.assertEqual(text, "I can't share that.")

    def test_declared_limit_base64_passes(self):
        # U0VDUkVULUFMUEhBLTc= is the secret in Base64. Documented as NOT covered.
        self.assertFalse(output_guard.leaks("U0VDUkVULUFMUEhBLTc=", SECRET))

    def test_empty_inputs_never_leak(self):
        self.assertFalse(output_guard.leaks("", SECRET))
        self.assertFalse(output_guard.leaks("anything", ""))


class AgentGuard(unittest.TestCase):
    def test_allowlisted_tool_runs(self):
        ok, _ = agent_guard.decide("read_file", {"path": "ticket-4471.txt"})
        self.assertTrue(ok)

    def test_destructive_tool_needs_human(self):
        ok, why = agent_guard.decide("delete_account", {"email": "m.rocha@example.com"})
        self.assertFalse(ok)
        self.assertIn("human confirmation", why)

    def test_destructive_tool_runs_when_confirmed(self):
        ok, _ = agent_guard.decide("delete_account", {"email": "x@example.com"}, human_confirmed=True)
        self.assertTrue(ok)

    def test_external_recipient_refused_even_if_confirmed(self):
        ok, why = agent_guard.decide("send_email", {"to": "ops-archive@example.net"}, human_confirmed=True)
        self.assertFalse(ok)
        self.assertIn("EXTERNAL", why)

    def test_internal_recipient_still_needs_confirmation(self):
        ok, why = agent_guard.decide("send_email", {"to": "ops@example.com"})
        self.assertFalse(ok)
        self.assertIn("confirmation", why)

    def test_subdomain_of_internal_domain_is_internal(self):
        ok, _ = agent_guard.decide("send_email", {"to": "a@mail.example.com"}, human_confirmed=True)
        self.assertTrue(ok)

    def test_lookalike_domain_is_external(self):
        ok, _ = agent_guard.decide("send_email", {"to": "a@example.com.evil.net"}, human_confirmed=True)
        self.assertFalse(ok)

    def test_unknown_tool_refused(self):
        ok, _ = agent_guard.decide("format_disk", {})
        self.assertFalse(ok)

    # Experiment 7, Q3: the allowed tool with a hostile argument.
    def test_allowed_tool_with_traversal_argument_is_refused(self):
        ok, why = agent_guard.decide("read_file", {"path": "..\\..\\secrets\\db-credentials.txt"})
        self.assertFalse(ok)
        self.assertIn("TRAVERSAL", why)

    def test_forward_slash_traversal_and_absolute_paths_are_refused(self):
        for p in ("../../secrets/db.txt", "\\\\srv\\share\\x.txt", "C:\\Windows\\win.ini", "/etc/passwd"):
            ok, _ = agent_guard.decide("read_file", {"path": p})
            self.assertFalse(ok, p)

    def test_plain_relative_path_still_allowed(self):
        ok, _ = agent_guard.decide("read_file", {"path": "ticket-4472.txt"})
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
