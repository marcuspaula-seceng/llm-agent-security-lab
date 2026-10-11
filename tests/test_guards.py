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


class PolicyBoundaryTests(unittest.TestCase):
    def test_allowlisting_destructive_tool_still_requires_confirmation(self):
        policy = agent_guard.Policy(allowlist=frozenset({"delete_account"}))
        self.assertFalse(agent_guard.decide("delete_account", {}, policy)[0])
        self.assertTrue(agent_guard.decide("delete_account", {}, policy, human_confirmed=True)[0])

    def test_allowlisting_side_effect_still_checks_recipient_and_confirmation(self):
        policy = agent_guard.Policy(allowlist=frozenset({"send_email"}))
        for confirmed in (False, True):
            self.assertFalse(agent_guard.decide(
                "send_email", {"to": "demo@example.net"}, policy, human_confirmed=confirmed)[0])
        self.assertFalse(agent_guard.decide("send_email", {"to": "demo@example.com"}, policy)[0])
        self.assertTrue(agent_guard.decide(
            "send_email", {"to": "demo@example.com"}, policy, human_confirmed=True)[0])

    def test_all_three_policy_categories_are_cumulative(self):
        policy = agent_guard.Policy(
            allowlist=frozenset({"send_email"}), destructive=frozenset({"send_email"}))
        self.assertFalse(agent_guard.decide(
            "send_email", {"to": "demo@example.net"}, policy, human_confirmed=True)[0])
        self.assertFalse(agent_guard.decide("send_email", {"to": "demo@example.com"}, policy)[0])
        self.assertTrue(agent_guard.decide(
            "send_email", {"to": "demo@example.com"}, policy, human_confirmed=True)[0])

    def test_malformed_argument_containers_fail_closed(self):
        for args in (None, [], "path", 42, True):
            with self.subTest(args=args):
                self.assertFalse(agent_guard.decide("read_file", args)[0])

    def test_malformed_tool_names_fail_closed(self):
        for name in (None, [], {}, 42):
            with self.subTest(name=name):
                self.assertFalse(agent_guard.decide(name, {})[0])

    def test_confirmation_requires_actual_boolean(self):
        for confirmed in ("false", "true", 1, [], None):
            with self.subTest(confirmed=confirmed):
                self.assertFalse(agent_guard.decide(
                    "delete_account", {}, human_confirmed=confirmed)[0])

    def test_model_argument_cannot_supply_confirmation(self):
        self.assertFalse(agent_guard.decide("delete_account", {"human_confirmed": True})[0])

    def test_path_values_are_not_coerced_to_strings(self):
        for path in (None, [], {}, 7, True, "", " ", "demo\x00.txt"):
            with self.subTest(path=path):
                self.assertFalse(agent_guard.decide("read_file", {"path": path})[0])

    def test_malformed_mailboxes_and_recipient_lists_fail_closed(self):
        for address in (
            None, [], 7, "example.com", "@example.com", "demo@@example.com",
            "demo@example.net,other@example.com", "demo@example.net;other@example.com",
            "Demo <demo@example.com>", "demo@example.com\n", "demo @example.com",
            "demo@.example.com", "demo@a..example.com", "demo@example.com.evil.net",
            "demo(comment)@example.com", "demo..name@example.com",
        ):
            with self.subTest(address=address):
                self.assertFalse(agent_guard.decide(
                    "send_email", {"to": address}, human_confirmed=True)[0])

    def test_valid_plain_mailboxes_remain_supported(self):
        for address in ("demo@example.com", "demo+audit@EXAMPLE.COM", "demo.name@mail.example.com"):
            with self.subTest(address=address):
                self.assertTrue(agent_guard.decide(
                    "send_email", {"to": address}, human_confirmed=True)[0])


if __name__ == "__main__":
    unittest.main()
