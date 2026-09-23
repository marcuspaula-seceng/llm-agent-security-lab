"""Per-task tool gate — the G1 guard from experiments 4/5.

The model sees every tool. The code decides which calls actually run:
  * only tools on the task's allowlist run without a human;
  * destructive tools always require explicit human confirmation;
  * side-effect tools (email) with a recipient outside the internal domains are refused.

Known limit (declared): this gates tool CALLS. It does not gate advice given in natural
language ("consider removing the account"). Nothing is executed; something may still be said.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Policy:
    allowlist: frozenset = field(default_factory=lambda: frozenset({"read_file", "lookup_ticket"}))
    destructive: frozenset = field(default_factory=lambda: frozenset({"delete_account"}))
    external_side_effect: frozenset = field(default_factory=lambda: frozenset({"send_email"}))
    internal_domains: tuple = ("example.com",)


def _domain_is_internal(address: str, internal_domains) -> bool:
    dom = str(address).split("@")[-1].lower().strip()
    return any(dom == d or dom.endswith("." + d) for d in internal_domains)


def decide(name: str, args: dict, policy: Policy = Policy(), human_confirmed: bool = False):
    """Return (allowed: bool, reason: str)."""
    if name in policy.allowlist:
        return True, "allowed by task allowlist"
    if name in policy.destructive:
        if human_confirmed:
            return True, "destructive tool confirmed by human"
        return False, "DESTRUCTIVE: requires explicit human confirmation"
    if name in policy.external_side_effect:
        to = str(args.get("to", ""))
        if not _domain_is_internal(to, policy.internal_domains):
            return False, f"EXTERNAL RECIPIENT {to!r}: refused"
        if human_confirmed:
            return True, "side effect confirmed by human"
        return False, "SIDE EFFECT outside task allowlist: requires confirmation"
    return False, "not in allowlist"
