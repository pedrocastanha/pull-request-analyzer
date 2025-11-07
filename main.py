import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from src.router import router as pr_analyzer_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting PR analyzer application...")
    yield

app = FastAPI(
    title="Azure Pull Request Analyzer",
    description="API for CI/CD using LangGraph to analyze Pull Requests by Pedro Castanheira.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pr_analyzer_router)

@app.get("/", tags=["Sistema"])
async def root():
    return {
        "app": "PR Analyzer",
        "status": "online",
        "docs_url": "/docs"
    }

@app.get("/health", tags=["Sistema"])
async def health_check():
    return {"status": "healthy"}