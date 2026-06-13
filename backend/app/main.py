from dotenv import load_dotenv
from braintrust import init_logger
from braintrust_langchain import BraintrustCallbackHandler, set_global_handler
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import router as api_router
load_dotenv()

init_logger(project="Compliance Agent", api_key=os.environ["BRAINTRUST_API_KEY"])
handler = BraintrustCallbackHandler()
set_global_handler(handler)


app = FastAPI(title="Compliance Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["localhost", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")
