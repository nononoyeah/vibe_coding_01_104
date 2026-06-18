from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.sessions import router as sessions_router
from app.config import settings
from app.db.app_store import ensure_app_db
from app.db.seed import ensure_biz_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_biz_db()
    ensure_app_db()
    yield


app = FastAPI(
    title="智能数据分析系统 API",
    description="基于 Qwen3 + LangChain + FastAPI 的智能数据分析后端",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions_router)
app.include_router(chat_router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "service": "智能数据分析系统",
        "version": "0.2.0",
        "phase": 3,
    }
