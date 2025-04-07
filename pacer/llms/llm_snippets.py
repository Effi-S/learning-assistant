"""
Mistral
===========
"""

from enum import StrEnum

from langchain.globals import set_llm_cache
from langchain_community.cache import SQLiteCache
from langchain_mistralai import ChatMistralAI

set_llm_cache(SQLiteCache(database_path=".langchain.db"))


class MistralModelName(StrEnum):
    MISTRAL_LATEST = "mistral-large-latest"
    CODESTRAL = "codestral-latest"


MISTRAL = ChatMistralAI(
    model=MistralModelName.MISTRAL_LATEST, timeout=6_000, temperature=0, top_p=1
)


"""
Perplexity
===========
Note: set PPLX_API_KEY
See Docs: https://docs.perplexity.ai/guides/getting-started
Models:             Cntext:
sonar-deep-research	128k
sonar-reasoning-pro	128k
sonar-reasoning	    128k
sonar-pro	        200k
sonar	            128k
r1-1776	            128k
"""


class SonarName(StrEnum):
    SONAR_DEEP_RESEARCH = "sonar-deep-research"
    SONAR_REASONING_PRO = "sonar-reasoning-pro"
    SONAR_REASONING = "sonar-reasoning"
    SONAR_PRO = "sonar-pro"
    SONAR = "sonar"
    R1_1776 = "r1-1776"


from langchain_community.chat_models import ChatPerplexity

perplexity = ChatPerplexity(model=SonarName.SONAR_DEEP_RESEARCH)
