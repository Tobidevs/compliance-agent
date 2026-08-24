import os

import braintrust
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .observability import init_langfuse
from .redaction import mask_value

load_dotenv()

# Set unconditionally: braintrust also picks BRAINTRUST_API_KEY up on its own, so the mask
# must be installed even when this module does not initialize the logger itself.
braintrust.set_masking_function(mask_value)

_braintrust_api_key = os.getenv("BRAINTRUST_API_KEY")
if _braintrust_api_key:
    from braintrust_langchain import BraintrustCallbackHandler, set_global_handler

    braintrust.init_logger(project="Compliance Agent", api_key=_braintrust_api_key)
    set_global_handler(BraintrustCallbackHandler())

# Configure Langfuse tracing (no-op if LANGFUSE_* keys are unset). After load_dotenv so
# the client never initializes with missing credentials.
init_langfuse()


app = FastAPI(title="Compliance Agent API")

# Credentialed CORS cannot use wildcards, so origins/methods/headers are all explicit.
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
CORS_ALLOW_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Authorization", "Content-Type"],
)

app.include_router(api_router, prefix="/api")
