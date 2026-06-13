from dotenv import load_dotenv

load_dotenv()  # must run before braintrust init so BRAINTRUST_API_KEY is in env

import braintrust

braintrust.init_logger(project="compliance-agent")
braintrust.auto_instrument()

# Agent module imports happen after auto_instrument() so LLM clients are patched
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router

app = FastAPI(title="Compliance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
