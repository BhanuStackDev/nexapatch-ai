"""Best-effort redaction of common secrets before AI context is prepared."""
from __future__ import annotations

import re

_REDACTED = "[REDACTED]"

_PRIVATE_KEY_BLOCK_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----.*?"
    r"-----END (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    re.DOTALL,
)

_SECRET_ASSIGNMENT_RE = re.compile(
    r"""
    (\b
    (?:[A-Z0-9_]*[_-])?
    (?:api[_-]?key|access[_-]?token|auth(?:entication)?[_-]?token|
       client[_-]?secret|password|passwd|pwd|
       secret(?:[_-]?(?:key|token|value))?|private[_-]?key|
       refresh[_-]?token|session[_-]?token|signing[_-]?key|
       database[_-]?url|connection[_-]?string|
       aws[_-]?secret[_-]?access[_-]?key|aws[_-]?access[_-]?key[_-]?id|
       jwt[_-]?secret|token)
    \b["']?\s*[:=]\s*)
    (?:"([^"\r\n]+)"|'([^'\r\n]+)'|([^\s,;}\]]+))
    """,
    re.IGNORECASE | re.VERBOSE,
)

_BEARER_TOKEN_RE = re.compile(
    r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}",
    re.IGNORECASE,
)

_KNOWN_TOKEN_RE = re.compile(
    r"""(?ix)
    (?<![A-Z0-9_-])
    (?:
        sk-(?:proj-|live-|test-)?[A-Z0-9_-]{16,}|
        sk_(?:live|test)_[A-Z0-9]{16,}|
        gsk_[A-Z0-9]{20,}|
        gh[pousr]_[A-Z0-9]{20,}|
        github_pat_[A-Z0-9_]{20,}|
        xox[baprs]-[A-Z0-9-]{10,}|
        AIza[A-Z0-9_-]{30,}|
        AKIA[A-Z0-9]{16}
    )
    (?![A-Z0-9_-])
    """
)

_JWT_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{10,}"
    r"\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"
    r"(?![A-Za-z0-9_-])"
)


def _replace_secret_assignment(match: re.Match[str]) -> str:
    prefix = match.group(1)

    if match.group(2) is not None:
        return f'{prefix}"{_REDACTED}"'
    if match.group(3) is not None:
        return f"{prefix}'{_REDACTED}'"
    return f"{prefix}{_REDACTED}"


def redact_secrets(text: str) -> str:
    """Redact common credential patterns; detection is not exhaustive."""
    text = _PRIVATE_KEY_BLOCK_RE.sub("[REDACTED PRIVATE KEY]", text)
    text = _SECRET_ASSIGNMENT_RE.sub(_replace_secret_assignment, text)
    text = _BEARER_TOKEN_RE.sub(
        lambda match: f"{match.group(0).split()[0]} {_REDACTED}",
        text,
    )
    text = _KNOWN_TOKEN_RE.sub("[REDACTED TOKEN]", text)
    text = _JWT_TOKEN_RE.sub("[REDACTED JWT]", text)
    return text
