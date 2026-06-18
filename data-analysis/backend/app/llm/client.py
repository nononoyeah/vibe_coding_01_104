from langchain_qwq import ChatQwQ

from app.config import settings


def get_llm() -> ChatQwQ:
    return ChatQwQ(
        model=settings.llm_model,
        api_key=settings.dashscope_api_key,
        base_url=settings.llm_base_url,
        max_retries=2,
        streaming=True,
    )
