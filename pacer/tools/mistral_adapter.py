from enum import StrEnum

from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_mistralai import ChatMistralAI

set_llm_cache(SQLiteCache(database_path=".langchain.db"))


class MistralModel(StrEnum):
    MISTRAL_LATEST = "mistral-large-latest"
    CODESTRAL = "codestral-latest"


mistral = ChatMistralAI(
    model=MistralModel.MISTRAL_LATEST, timeout=6_000, temperature=0, top_p=1
)