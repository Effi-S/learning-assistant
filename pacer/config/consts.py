from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

ROOT_DIR = Path(__file__).parent.parent.parent

ENV = ROOT_DIR / ".env"
assert ENV.exists(), f"Missing .env file: {ENV}"
assert load_dotenv(ENV)

# DEFAULT_LLM = ChatOpenAI(model="gpt-4o")
DEFAULT_EMBEDDING = OpenAIEmbeddings(model="text-embedding-3-large")


iframe = """
    <style>
        iframe {{
            width: 100%;
            height: 300px !important;
            min-height: 600px !important;
            border: none;
            background-color: #f0f0f0; /* Debug visibility */
        }}
    </style>
    <iframe src="{}" width="100%" height="100%" frameborder="0"></iframe>
    """
