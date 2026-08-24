"""Secret redaction applied to trace payloads before they leave the process.

Provider-neutral on purpose: this used to live inside the Langfuse module, which made it
the only redaction in the system and tied it to the one exporter being retired. Langfuse is
gone; `mask_value` is registered on Braintrust via `set_masking_function` in main.py and
stays exporter-agnostic so the next consolidation cannot lose redaction either.
"""

import re

# Conservative redaction of credential-like tokens before anything is exported.
# Kept tight so normal source code / compliance text is never mangled.
_SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9\-_]{8,}|pk-lf-[A-Za-z0-9\-]{6,}|gh[pousr]_[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._\-+/]+=*)"
)


def mask_value(data):
    """Recursively redact secret-like strings in a trace payload."""
    if isinstance(data, str):
        return _SECRET_RE.sub("[REDACTED]", data)
    if isinstance(data, dict):
        return {key: mask_value(value) for key, value in data.items()}
    if isinstance(data, (list, tuple)):
        return [mask_value(value) for value in data]
    return data
