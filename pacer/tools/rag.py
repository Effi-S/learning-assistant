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
from langchain_chroma import Chroma
from langchain_community.document_loaders import (
    BSHTMLLoader,
    DirectoryLoader,
    PyPDFLoader,
    TextLoader,
    WikipediaLoader,
)
from langchain_core.documents.base import Document
from langchain_core.vectorstores import VectorStore

# from pacer.config import consts
from pacer.config import consts
from pacer.config.llm_adapter import LLMSwitch
from pacer.models.code_cell_model import JupyterCells

assert dotenv.load_dotenv(consts.ENV)


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
    llm = llm or LLMSwitch.get_current()
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
        return loader.load()
    elif isinstance(source, str):
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as temp_pdf:
            pdf_bytes = base64.b64decode(source)
            temp_pdf.write(pdf_bytes)
            temp_pdf.flush()
            loader = PyPDFLoader(temp_pdf.name)
            pages = loader.load()
            return pages
    else:
        NotImplemented(f"Reading PDF from: `{type(source)}` Not implemented.")


def split_documents(*documents: list[Document | str]) -> list[Document]:

    # Usage errors
    if not documents:
        raise ValueError("`documents` cannot be empty")

    if len(documents) == 1 and isinstance(documents[0], list):
        documents = documents[0]
    # --

    documents = [
        Document(page_content=doc) if isinstance(doc, str) else doc for doc in documents
    ]

    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(chunk_size=500)
    docs = text_splitter.split_documents(documents)
    return docs


def split_text(text: str) -> list[Document]:
    return split_documents(Document(page_content=text))


def insert_docs(
    docs: list[Document],
    embedding_function=None,
    sub_dir: str = None,
    vectorsore: VectorStore = Chroma,
) -> VectorStore:
    """Inserting previously split documents into a Chroma DB"""
    embedding_function = embedding_function or consts.DEFAULT_EMBEDDING

    persist_directory = consts.ROOT_DIR / f".chroma_persist"
    if sub_dir:
        persist_directory /= sub_dir

    if persist_directory.exists():
        db = vectorsore(
            embedding_function=embedding_function,
            persist_directory=str(persist_directory),
        )

        existing_docs = db.get().get("documents", {})  # TODO: may not be generic enough
        new_docs = [doc for doc in docs if doc.page_content not in existing_docs]
        if new_docs:
            db.add_documents(new_docs)

        return db
    db = vectorsore.from_documents(
        docs, embedding_function, persist_directory=str(persist_directory)
    )

    return db


def create_summary(split_docs: list[Document], chain_type="refine", llm=None) -> str:
    """Create a summary based on split documents
    See: https://python.langchain.com/docs/tutorials/summarization/
    Example Usage:
        >>> pages = read_pdf('example.pdf')
        >>> ss = split_documents(pages)
        >>> print(create_summary(ss))
    """
    llm = llm or LLMSwitch.get_current()
    if len(split_docs) == 1:
        doc = split_docs[0].page_content
        try:
            return llm.invoke(
                f"Please create a detailed Summary of the following:\n{doc}"
            ).content
        except Exception as e:
            print(
                "********\n"
                f"*** Warning could not create single Doc summary:\n{e}\n"
                "..Trying summary chain..\n*******"
            )
            split_docs = split_documents(*split_docs)
    chain = load_summarize_chain(llm, chain_type=chain_type)
    ret = chain.invoke(split_docs)

    # ret has `input_documents` as well but we already have that,
    # seems safe to return the output_text only
    # Maybe I missed something.
    return ret["output_text"]


def get_multi_query(question, db, llm=None) -> list[Document]:
    """Creating langchain MultiQuery
        More info here: https://arxiv.org/abs/2305.13245
    Example usage:
        >>> pages = read_pdf('example.pdf')
        >>> ss = split_documents(pages)
        >>> db = insert_docs(ss)
        >>> print(get_multi_query("What is the author's name?", db=db))
    """
    # -- verbose multi-query --
    logging.basicConfig()
    logger = logging.getLogger("langchain.retrievers.multi_query")
    logger.setLevel(logging.INFO)
    # -- -- --

    llm = llm or LLMSwitch.get_current()
    retriever_from_llm = MultiQueryRetriever.from_llm(
        retriever=db.as_retriever(), llm=llm
    )
    docs = retriever_from_llm.get_relevant_documents(query=question)
    return docs


def compress_and_ask(question: str, db, llm=None) -> list[Document]:
    """See: https://python.langchain.com/docs/how_to/contextual_compression/"""
    llm = llm or LLMSwitch.get_current()

    # --1-- Compress docs

    compressor = LLMChainExtractor.from_llm(llm)
    compression_retriever = ContextualCompressionRetriever(
        base_retriever=db.as_retriever(), base_compressor=compressor
    )

    # --2-- Ask the compress docs a question
    compressed_docs = compression_retriever.invoke(question)

    return compressed_docs


_subject_filter_prompt = ChatPromptTemplate.from_template(
    """Given the following context:
{context}

List in bullet points the practical code that a student reading this article should learn.
If you cannot find any code, leave this empty."""
)

_code_cell_prompt = ChatPromptTemplate.from_template(
    """
Create a Jupyter Notebook that can help practice coding.
Prefer adding Markdown Cells to explain the over comments in the code.
Base the Notebook on the following context from multiple documents:
{context}


"""
)


def create_jupyter_cells(
    db, llm=None, prompt_template: Optional[ChatPromptTemplate] = None
):
    prompt = prompt_template or _code_cell_prompt
    llm = llm or LLMSwitch.get_current()

    retriever = db.as_retriever(search_kwargs={"k": 30})
    context_docs = retriever.invoke("")
    context = "\n----\n".join(doc.page_content for doc in context_docs)

    if (
        len(context) > 128_000
    ):  # TODO: find a better way to determine context limit of LLM
        context = create_summary(context_docs)

    chain = prompt | llm.with_structured_output(JupyterCells, method="function_calling")
    result = chain.invoke({"context": context})
    return result


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
