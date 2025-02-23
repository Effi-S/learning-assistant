from itertools import chain
from uuid import uuid4

from sqlalchemy.orm import Session

from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm import base
from pacer.orm.file_orm import File, FileStatus
from pacer.orm.project_orm import Project

SessionLocal = base.make_session()


def list_projects(session: Session = None) -> list[str]:
    with SessionLocal() as session:
        return list(chain(*session.query(Project.name).all()))


def list_files(project_name: str) -> list[FileEntry]:
    with SessionLocal() as session:
        project = session.query(Project).filter_by(name=project_name).first()
        entries = list(map(FileEntry.model_validate, project.files))
        return entries


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
