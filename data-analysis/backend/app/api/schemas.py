from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class SessionOut(BaseModel):
    id: str
    title: str
    messages: list[dict] = Field(default_factory=list)
    chartOption: dict | None = None
    updatedAt: int


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=4000)
