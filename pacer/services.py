from collections import defaultdict
from itertools import chain
from pathlib import Path
from uuid import uuid4

from langchain.schema import Document
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from pacer.models.code_cell_model import Code
from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm import base
from pacer.orm.code_orm import CodeCell
from pacer.orm.file_orm import File, FileStatus, FileType
from pacer.orm.note_orm import Note
from pacer.orm.project_orm import Project
from pacer.quiz import quiz_creater
from pacer.tools import rag

SessionLocal = base.make_session()


def list_projects(session: Session = None) -> list[str]:
    with SessionLocal() as session:
        return list(chain(*session.query(Project.name).all()))


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
            data={"title": doc.metadata["title"]},
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
        file.data["summary"] = str(summary)
        flag_modified(file, "data")  #  the ORM may not detect changes automatically
        session.commit()


def read_sources(sources: list[FileEntry]) -> list[Document]:
    """Converts FileEntries to LangChain Documents
    (perhaps this should move to file_entry.py)"""
    text_types = [FileType.TEXT, FileType.URL, FileType.MARKDOWN]
    docs = []
    for entry in sources:
        match entry.type_:
            case FileType.PDF:
                docs.extend(rag.read_pdf(entry.content))
            case t if t in text_types:
                docs.append(Document(page_content=entry.content))
            case _:
                docs.append(Document(page_content=entry.content))

    return docs


def get_quiz(project_name: str) -> quiz_creater.Quiz:
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
        if "quiz" in project.data:
            # Adds new questions
            quiz = get_quiz(project_name=project_name)
            quiz = quiz_creater.add_questions(docs, quiz)
        else:
            quiz = quiz_creater.create_quiz(docs)
        project.data["quiz"] = quiz.model_dump_json(indent=2)
        flag_modified(project, "data")  #  the ORM may not detect changes automatically
        session.commit()
        return quiz


def create_practice(project_name: str) -> quiz_creater.Quiz:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        files = list(map(FileEntry.model_validate, project.files))
        docs = read_sources(files)
        quiz = quiz_creater.create_quiz(docs)
        project.data["practice"] = quiz.model_dump_json(indent=2)
        flag_modified(project, "data")  #  the ORM may not detect changes automatically
        session.commit()
        return quiz


def get_practice(project_name: str) -> quiz_creater.Quiz:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        q = project.data.get("practice")
        if q:
            return quiz_creater.Quiz.model_validate_json(q)


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


def update_note(note: Note, new_note: str) -> Note:
    with SessionLocal() as session:
        note = session.query(Note).filter(Note.id == note.id).first()  # avoid detach
        note.content = new_note
        session.commit()


def create_cells(project_name: str) -> Note:
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        note = Note(project_id=project.id, content=note)

        session.add(note)
        session.commit()
        return note


def get_codes(project_name: str) -> list[CodeCell]:
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        return project.code_cells


def update_codee(code: Code, new_code: str) -> Code:
    with SessionLocal() as session:
        code = session.query(CodeCell).filter(CodeCell.id == code.id).first()
        code.code = new_code
        session.commit()


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
