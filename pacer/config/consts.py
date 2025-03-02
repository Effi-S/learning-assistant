from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

ROOT_DIR = Path(__file__).parent.parent.parent

ENV = ROOT_DIR / ".env"
assert ENV.exists(), f"Missing .env file: {ENV}"
assert load_dotenv(ENV)

DEFAULT_LLM = ChatOpenAI(model="gpt-4o")
DEFAULT_EMBEDDING = OpenAIEmbeddings(model="text-embedding-3-large")
