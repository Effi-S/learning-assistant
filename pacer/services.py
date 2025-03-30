from collections import defaultdict
from itertools import chain
from pathlib import Path
from typing import Generator, Optional
from uuid import uuid4

from langchain.schema import Document
from sqlalchemy import desc
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from pacer.config.llm_adapter import LLMSwitch
from pacer.models.code_cell_model import JupyterCells
from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm import base
from pacer.orm.chat_message_orm import ChatMessage
from pacer.orm.file_orm import File, FileStatus, FileType
from pacer.orm.note_orm import Note
from pacer.orm.project_orm import Project
from pacer.quiz import quiz_creater
from pacer.tools import rag

SessionLocal = base.make_session()


def list_projects(session: Session = None) -> list[str]:
    with SessionLocal() as session:
        query = session.query(Project.name).order_by(desc(Project.created_at))
        return list(chain(*query.all()))


def list_files(project_name: str) -> list[FileEntry]:
    with SessionLocal() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        entries = list(map(FileEntry.model_validate, project.files))
        return entries


def add_project(project_name: str) -> ProjectData:
    with SessionLocal() as session:
        project = Project(id=str(uuid4()), name=project_name)
        session.add(project)
        session.commit()
        return ProjectData.model_validate(project)


def add_files(file_entries: list[FileEntry]) -> list[File]:
    if not file_entries:
        return
    with SessionLocal() as session:
        project = file_entries[0].project_ref
        if not project.id:
            project = session.query(Project).filter_by(name=project.name).first()

        files = [
            File(
                id=str(uuid4()),
                type=file_entry.type_,
                project_id=project.id,
                filepath=file_entry.filepath,
                content=file_entry.content,
                status=FileStatus.CREATED,
            )
            for file_entry in file_entries
        ]

        session.add_all(files)
        session.commit()
        return files


def add_url(url: str, project_name: str) -> list[File]:
    docs = rag.read_url(url)
    entries = [
        FileEntry(
            content=doc.page_content,
            filepath=url,
            type=FileType.URL,
            data=doc.metadata,
            project_ref=ProjectData(name=project_name),
        )
        for doc in docs
    ]
    return add_files(entries)


def delete_project(project_name: str):
    with SessionLocal() as session:
        session.query(Project).filter(Project.name == project_name).delete(
            synchronize_session="fetch"
        )
        session.commit()


def delete_file(file_entry: FileEntry):
    with SessionLocal() as session:
        session.query(File).filter(
            (File.project_id == str(file_entry.project_ref.id))
            & (File.filepath == file_entry.filepath)
        ).delete(synchronize_session="fetch")
        session.commit()


def add_summary_to_file(file_entry: FileEntry):
    """Adds both to `FileEntry` and `File` (in ORM)"""
    # suffix = Path(file_entry.filepath).suffix
    if file_entry.type_ in (FileType.MARKDOWN, FileType.TEXT, FileType.URL):
        split = rag.split_text(file_entry.content)
    elif file_entry.type_ in (FileType.PDF,):
        split = rag.read_pdf(file_entry.content)
    else:
        raise ValueError(f"Unkown type: `{file_entry.type_}`")

    print("Summary:")
    summary = rag.create_summary(split)
    print(summary)

    with SessionLocal() as session:
        file = session.query(File).filter(File.id == str(file_entry.id)).one()
        if not file.data:
            file.data = {}
        file_entry.data["summary"] = file.data["summary"] = str(summary)
        flag_modified(file, "data")  #  the ORM may not detect changes automatically
        session.commit()


def iter_read_entry(entry: FileEntry) -> Generator[None, None, Document]:
    text_types = [FileType.TEXT, FileType.URL, FileType.MARKDOWN]
    match entry.type_:
        case FileType.PDF:
            yield from rag.read_pdf(entry.content)
        case t if t in text_types:
            yield Document(page_content=entry.content)
        case _:
            yield Document(page_content=entry.content)


def read_sources(sources: list[FileEntry]) -> list[Document]:
    """Converts FileEntries to LangChain Documents
    (perhaps this should move to file_entry.py)"""
    docs = [doc for entry in sources for doc in iter_read_entry(entry)]
    return docs


def get_quiz(project_name: str) -> Optional[quiz_creater.Quiz]:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        q = project.data.get("quiz")
        if q:
            return quiz_creater.Quiz.model_validate_json(q)


def create_quiz(project_name: str) -> quiz_creater.Quiz:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        files = list(map(FileEntry.model_validate, project.files))
        docs = read_sources(files)

        quiz = get_quiz(project_name=project_name)
        if quiz:
            quiz = quiz_creater.add_questions(docs, quiz)
        else:
            quiz = quiz_creater.create_quiz(docs)
        project.data["quiz"] = quiz.model_dump_json(indent=2)
        flag_modified(project, "data")  #  the ORM may not detect changes automatically
        session.commit()
        return quiz


def remove_quiz(project_name: str) -> None:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        project.data.pop("quiz", None)
        flag_modified(project, "data")  #  the ORM may not detect changes automatically
        session.commit()


def create_jupyter_cells(project_name: str) -> JupyterCells:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        files = list(map(FileEntry.model_validate, project.files))
        docs = read_sources(files)
        db = rag.insert_docs(docs, sub_dir=project_name)
        cells: JupyterCells = rag.create_jupyter_cells(db=db)
        return cells


def update_jupyter_cells(
    project_name: str, cells: JupyterCells, update: str
) -> JupyterCells:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        files = list(map(FileEntry.model_validate, project.files))
        docs = read_sources(files)
        db = rag.insert_docs(docs, sub_dir=project_name)
        cells: JupyterCells = rag.update_jupyter_cells(
            db=db, notebook_cells=cells, user_message=update
        )
        return cells


def add_note(note: str, project_name: str) -> Note:
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        note = Note(project_id=project.id, content=note)

        session.add(note)
        session.commit()
        return note


def get_notes(project_name: str) -> list[Note]:
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        return project.notes


def remove_note(note: Note):
    with SessionLocal() as session:
        session.delete(note)
        session.commit()


def update_note(note: Note, new_note: str) -> Note:
    with SessionLocal() as session:
        note = session.query(Note).filter(Note.id == note.id).first()  # avoid detach
        note.content = new_note
        session.commit()


def get_messages(project_name: str) -> list[ChatMessage]:
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        return project.chat_messages


def ask(messages, context_files: list[FileEntry] = None, *args, llm=None, **kwargs):
    """Ask An AI Agent about a question relating to docs"""
    llm = llm or LLMSwitch.get_current()
    if not context_files:
        return llm.invoke(messages, *args, **kwargs)

    docs = read_sources(context_files)
    db = rag.insert_docs_non_persistant(docs=docs)
    resp = rag.context_chat(messages=messages, db=db)
    return resp


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
