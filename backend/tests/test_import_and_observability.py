"""Phase 4.6 / 3.6 / 5.2 — clean import, and redaction surviving the Braintrust consolidation.

Invariant 5: `from agent.agent import compliance_agent` must import with no stubs, no
credentials and no sockets. It is run in a subprocess because the pytest process has already
imported the module, so an in-process check proves nothing about a cold start.
"""

import subprocess
import sys
import textwrap
from pathlib import Path

import braintrust
from braintrust import logger as braintrust_logger

from app.redaction import mask_value

BACKEND = Path(__file__).resolve().parents[1]

# Cleared in the subprocess so an accidental credential read fails instead of succeeding.
CREDENTIAL_VARS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "PINECONE_API_KEY",
    "GITHUB_PERSONAL_ACCESS_TOKEN",
    "BRAINTRUST_API_KEY",
    "LANGSMITH_API_KEY",
]


def run_cold_import(body: str) -> subprocess.CompletedProcess:
    script = textwrap.dedent(
        f"""
        import os, socket
        for name in {CREDENTIAL_VARS!r}:
            os.environ.pop(name, None)

        def blocked(*args, **kwargs):
            raise AssertionError("import opened a socket")

        socket.socket.connect = blocked
        socket.socket.connect_ex = blocked
        socket.create_connection = blocked

        {body}
        print("OK")
        """
    )
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_importing_the_graph_opens_no_socket_and_reads_no_credentials():
    result = run_cold_import("from agent.agent import compliance_agent")

    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_importing_the_api_layer_is_side_effect_free():
    result = run_cold_import("import app.main")

    assert result.returncode == 0, result.stderr


def test_importing_the_eval_runner_does_not_log_in_to_braintrust():
    # Eval(...) at module scope attempted a network login on import and fired a real 401.
    result = run_cold_import("import evals.run_evals")

    assert result.returncode == 0, result.stderr


# ---------------------------------------------------------------------------
# 5.2 — redaction is the one thing the Langfuse deletion could have lost
# ---------------------------------------------------------------------------
def test_mask_is_registered_on_braintrust():
    braintrust.set_masking_function(mask_value)

    # Read it back off Braintrust's own state: registration is the property, not the call.
    background_logger = braintrust_logger._state.global_bg_logger()
    installed = next(
        getattr(background_logger, name)
        for name in dir(background_logger)
        if "mask" in name and getattr(background_logger, name, None) is mask_value
    )
    assert installed is mask_value


def test_credential_like_strings_are_redacted():
    payload = {
        "prompt": "export OPENAI_API_KEY=sk-proj-AbCdEf123456789012345",
        "headers": {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.abc"},
        "files": ["token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ012345 in .env"],
    }

    masked = str(mask_value(payload))

    assert "sk-proj" not in masked
    assert "ghp_" not in masked
    assert "eyJhbGciOiJIUzI1NiJ9" not in masked
    assert masked.count("[REDACTED]") == 3


def test_masking_recurses_through_nested_containers():
    masked = mask_value({"a": [{"b": ("sk-live-ABCDEFGHIJKL",)}]})

    assert masked["a"][0]["b"] == ["[REDACTED]"]


def test_ordinary_source_code_is_not_mangled():
    code = "const config = { matcher: ['/dashboard/:path*'] } // sk not a key"

    assert mask_value(code) == code


def test_langfuse_is_fully_gone():
    """5.2: one exporter. A re-added import would restore double export and double PII.

    Matches imports rather than the word, so the historical note in redaction.py's docstring
    stays allowed — that comment is why the mask outlived the module.
    """
    offenders = []
    for path in BACKEND.rglob("*.py"):
        if ".venv" in path.parts or "tests" in path.parts:
            continue
        text = path.read_text()
        if "import langfuse" in text or "from langfuse" in text:
            offenders.append(str(path.relative_to(BACKEND)))

    assert offenders == []
    assert not (BACKEND / "app" / "observability.py").exists()
    assert not (BACKEND / "evals_langfuse").exists()
    assert "langfuse" not in (BACKEND / "requirements.txt").read_text().lower()
