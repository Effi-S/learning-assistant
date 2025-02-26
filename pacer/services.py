from collections import defaultdict
from itertools import chain
from pathlib import Path
from uuid import uuid4

from langchain.schema import Document
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm import base
from pacer.orm.file_orm import File, FileStatus
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
    suffix = Path(file_entry.filepath).suffix
    if suffix in (".txt", ".py"):
        split = rag.split_text(file_entry.content)
    elif suffix in (".pdf"):
        split = rag.read_pdf(file_entry.content)
    else:
        raise ValueError(f"Unkown type: `{suffix}`")

    print("Summary:")
    summary = rag.create_summary(split)
    print(summary)

    with SessionLocal() as session:
        file = session.query(File).filter(File.id == str(file_entry.id)).one()
        if not file.data:
            file.data = {}
        file.data["summary"] = summary
        flag_modified(file, "data")  #  the ORM may not detect changes automatically
        session.commit()


def read_sources(sources: list[FileEntry]) -> list[Document]:
    suffix2entries = defaultdict(list)
    for entry in sources:
        suffix2entries[Path(entry.filepath).suffix].append(entry)
    pdf_entries, text_entries = suffix2entries[".pdf"], suffix2entries[".txt"]

    docs = []
    for entry in pdf_entries:
        docs += rag.read_pdf(entry.content)
    for entry in text_entries:
        docs.append(Document(page_content=entry.content))

    return docs


def create_quiz(project_name: str) -> quiz_creater.Quiz:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        files = list(map(FileEntry.model_validate, project.files))
        docs = read_sources(files)
        quiz = quiz_creater.create_quiz(docs)
        project.data["quiz"] = quiz.model_dump_json(indent=2)
        flag_modified(project, "data")  #  the ORM may not detect changes automatically
        session.commit()
        return quiz


def get_quiz(project_name: str) -> quiz_creater.Quiz:
    assert project_name
    with SessionLocal() as session:
        project = session.query(Project).filter(Project.name == project_name).first()
        q = project.data.get("quiz")
        if q:
            return quiz_creater.Quiz.model_validate_json(q)


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
