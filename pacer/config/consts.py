from pathlib import Path

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

ROOT_DIR = Path(__file__).parent.parent

DEFAULT_LLM = ChatOpenAI(model="gpt-4o")
DEFAULT_EMBEDDING = OpenAIEmbeddings(model="text-embedding-3-large")
