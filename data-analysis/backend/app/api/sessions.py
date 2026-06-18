from fastapi import APIRouter, HTTPException

from app.api.schemas import SessionCreate, SessionOut
from app.db import app_store

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions():
    return app_store.list_sessions()


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: SessionCreate):
    return app_store.create_session(body.title)


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str):
    session = app_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session


@router.get("/{session_id}/messages")
def get_session_messages(session_id: str):
    session = app_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return session["messages"]


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: str):
    if not app_store.delete_session(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
