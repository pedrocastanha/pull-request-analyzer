import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pull Requests Analyzer",
    description="Analista de Pull Requests para padronização e boas práticas de programação.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health", tags=["Sistema"])
async def health_check():
    return {"status": "healthy"}