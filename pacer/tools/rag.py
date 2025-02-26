import base64
import logging
import subprocess
import tempfile
import urllib
from pathlib import Path
from typing import Optional

import dotenv
from langchain.chains.summarize import load_summarize_chain
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import (
    EmbeddingsFilter,
    LLMChainExtractor,
)
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import (
    BSHTMLLoader,
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
    WikipediaLoader,
)
from langchain_community.vectorstores import Chroma
from langchain_core.documents.base import Document

from pacer.config import consts

dotenv.load_dotenv()


def read_wikipedia(subject: str, load_max_docs: int = 1) -> list[Document]:
    """(Dependency: wikipedia)"""
    loader = WikipediaLoader(query=subject, load_max_docs=load_max_docs)
    ret = loader.load()
    assert ret, f"Could not find anything in Wikipedia for: {subject}"
    return ret


def ask_wiki(
    subject: str, question: str, llm=None, load_max_docs: int = 1
) -> list[Document]:
    """Get Wikipedia context on a subject and ask an LLM about said context.
    Example usage:
        In [1]: ask_wiki(subject='Cryptography', question='What is a cryptographic hash function?')
        Out[1]: 'System: A cryptographic hash function is a mathematical algorithm that
                takes input data of any size and produces a fixed-size output known as a hash value...'
    (Dependency: wikipedia)"""
    llm = llm or consts.DEFAULT_LLM
    context = read_wikipedia(query=subject, load_max_docs=load_max_docs)

    sys_msg = SystemMessagePromptTemplate.from_template(
        "You are an expert with facts about {subject}, here is some context:\n{context[0].page_content}"
    )
    human_msg = HumanMessagePromptTemplate.from_template(
        "{question}\nExpand based on your context knowledge."
    )
    chat_template = ChatPromptTemplate.from_messages(
        [sys_msg, human_msg]
    ).format_prompt(subject=subject, question=question, context=context)
    answer = llm.invoke(chat_template)
    return answer


def read_url(url: str) -> list[Document]:
    """(Dependencies: beautifulsoup4, lxml, urllib)"""
    # -- request URL --
    resp = urllib.request.urlopen(url)

    # -- store response in temporary file
    temp = tempfile.NamedTemporaryFile()
    with open(temp.name, "wb+") as wfl:
        wfl.write(resp.read())

    # -- load data with beautifulsoup
    loader = BSHTMLLoader(temp.name)
    data = loader.load()
    return data


def read_repo(
    github_url: str, target_dir: Optional[Path | str] = None
) -> list[Document]:
    """Read a github Repo into Document Objects.
    :target_dir:  location to store github Repo for reuse
    dependency: pip install unstructured[md]"""
    if not target_dir:
        target_dir = Path(tempfile.TemporaryDirectory().name)
    elif isinstance(target_dir, str):
        target_dir = Path(target_dir)

    if not target_dir.exists():
        raise FileNotFoundError(f"Target Directory: {target_dir} does not exist!")

    if any(target_dir.glob("*")):
        target_dir = target_dir / Path(github_url).stem

    if not any(target_dir.glob("*")):
        cmd = ["git", "clone", github_url, str(target_dir)]
        proc = subprocess.run(cmd, text=True, capture_output=True)
        print(proc.stdout)
        if proc.returncode:
            raise ValueError(f'{" ".join(cmd)} Failed!\n{proc.stderr}')

    loader = DirectoryLoader(target_dir, glob="**/*", show_progress=True)
    docs = loader.load()
    return docs


def read_pdf(source: Path | str) -> list[Document]:
    """(Dependency: pypdf )"""
    if isinstance(source, Path):
        loader = PyPDFLoader(str(source))
        return loader.load_and_split()
    elif isinstance(source, str):
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
            pdf_bytes = base64.b64decode(source)
            temp_pdf.write(pdf_bytes)
            temp_pdf.flush()
            loader = PyPDFLoader(temp_pdf.name)
            pages = loader.load_and_split()
            return pages
    else:
        NotImplemented(f"Reading PDF from: `{type(source)}` Not implemented.")


def split_documents(*documents: list[Document | str]) -> list[Document]:
    documents = [
        Document(page_content=doc) if isinstance(doc, str) else doc for doc in documents
    ]

    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(chunk_size=500)
    docs = text_splitter.split_documents(documents)
    return docs


def split_text(text: str) -> list[Document]:
    return split_documents(Document(page_content=text))


def insert_split_docs(
    docs: list[Document], embedding_function=None, sub_dir: str = None
) -> Chroma:
    """Inserting previously split documents into a Chroma DB"""
    embedding_function = embedding_function or consts.DEFAULT_EMBEDDING

    persist_directory = consts.ROOT_DIR / ".chroma_persist"
    if sub_dir:
        persist_directory /= sub_dir
    db = Chroma.from_documents(
        docs, embedding_function, persist_directory=persist_directory
    )

    return db


def create_summary(
    split_documents: list[Document], chain_type="refine", llm=None
) -> str:
    """Create a summary based on split documents
    See: https://python.langchain.com/docs/tutorials/summarization/
    Example Usage:
        >>> pages = read_pdf('example.pdf')
        >>> ss = split_documents(pages)
        >>> print(create_summary(ss))
    """
    llm = llm or consts.DEFAULT_LLM
    chain = load_summarize_chain(llm, chain_type=chain_type)
    ret = chain.invoke(split_documents)

    # ret has `input_documents` as well but we already have that,
    # seems safe to returning the output_text only
    # Maybe I missed something.
    return ret["output_text"]


def get_multi_query(question, db, llm=None) -> list[Document]:
    """Creating langchain MultiQuery
        More info here: https://arxiv.org/abs/2305.13245
    Example usage:
        >>> pages = read_pdf('example.pdf')
        >>> ss = split_documents(pages)
        >>> db = insert_split_docs(ss)
        >>> print(get_multi_query("What is the author's name?", db=db))
    """
    # -- verbose multi-query --
    logging.basicConfig()
    logger = logging.getLogger("langchain.retrievers.multi_query")
    logger.setLevel(logging.INFO)
    # -- -- --

    llm = llm or consts.DEFAULT_LLM
    retriever_from_llm = MultiQueryRetriever.from_llm(
        retriever=db.as_retriever(), llm=llm
    )
    docs = retriever_from_llm.get_relevant_documents(query=question)
    return docs


def compress_and_ask(question: str, db, llm=None) -> list[Document]:
    """See: https://python.langchain.com/docs/modules/data_connection/retrievers/contextual_compression/"""
    llm = llm or consts.DEFAULT_LLM

    # --1-- Compress docs
    compressor = LLMChainExtractor.from_llm(llm)
    retriever = ContextualCompressionRetriever(
        base_retriever=db.as_retriever(), base_compressor=compressor
    )

    compressed_docs = retriever.get_relevant_documents(question)

    # --2-- Ask the compress docs a question

    return compressed_docs


def contextual_filter(
    filter_query: str, db, llm=None, embedding_function=None
) -> list[Document]:
    llm = llm or consts.DEFAULT_LLM
    embedding_function = embedding_function or consts.DEFAULT_EMBEDDING
    embeddings_filter = EmbeddingsFilter(
        embeddings=embedding_function, similarity_threshold=0.76
    )
    retriever = ContextualCompressionRetriever(
        base_retriever=db.as_retriever(), base_compressor=embeddings_filter
    )

    compressed_docs = retriever.get_relevant_documents(filter_query)
    return compressed_docs


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
