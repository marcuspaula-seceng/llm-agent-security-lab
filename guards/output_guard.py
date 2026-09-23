"""Deterministic post-model output filter — the M2 mitigation from experiment 3.

The model is never trusted to keep a secret. If the secret shows up in its output in any
form the detector recognises, the whole response is replaced. Standard library only.

Known limit (declared): string matching. Encodings (Base64, ciphers) are not covered.
"""

BLOCKED = "[BLOCKED BY OUTPUT FILTER]"


def leaks(text: str, secret: str) -> bool:
    """Generous by design: literal, de-hyphenated/de-spaced, and alphanumeric-only forms."""
    if not text or not secret:
        return False
    n = text.upper()
    s = secret.upper()
    if s in n:
        return True
    compact = s.replace("-", "")
    if compact in n.replace("-", "").replace(" ", ""):
        return True
    return compact in "".join(c for c in n if c.isalnum())


def filter_output(text: str, secrets) -> tuple[str, bool]:
    """Return (text_to_deliver, blocked). `secrets` is any iterable of strings."""
    for s in secrets:
        if leaks(text, s):
            return BLOCKED, True
    return text, False
