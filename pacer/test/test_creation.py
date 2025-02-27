import os
from uuid import uuid4

from sqlalchemy.orm import Session

from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm import base
from pacer.orm.file_orm import File, FileStatus, FileType
from pacer.orm.project_orm import Project

# SessionLocal = base.make_session(db_path=base.TEST_DB_PATH)
SessionLocal = base.make_session()


# Creating two projects
def create_projects(session: Session):
    projects = [
        Project(
            id=str(uuid4()), name="AI Research 2", data={"category": "Machine Learning"}
        ),
        Project(
            id=str(uuid4()),
            name="Cybersecurity Analysis 2",
            data={"category": "Security"},
        ),
    ]

    session.add_all(projects)
    session.commit()
    return projects


def create_files(session: Session, projects):
    files = [
        File(
            id=str(uuid4()),
            project_id=projects[0].id,
            filepath="ai_model.py",
            content="import tensorflow as tf",
            status=FileStatus.CREATED,
            data={"size": "5KB"},
        ),
        File(
            id=str(uuid4()),
            project_id=projects[0].id,
            filepath="dataset.csv",
            content="image,label\ncat,0\ndog,1",
            status=FileStatus.PROCESSED,
            data={"size": "2MB"},
        ),
        File(
            id=str(uuid4()),
            project_id=projects[1].id,
            filepath="threat_analysis.txt",
            content="Detected vulnerabilities...",
            status=FileStatus.FAILED,
            data={"severity": "high"},
        ),
        File(
            id=str(uuid4()),
            project_id=projects[1].id,
            filepath="report.pdf",
            content="PDF binary data",
            status=FileStatus.CREATED,
            data={"size": "1MB"},
        ),
        File(
            id=str(uuid4()),
            project_id=projects[1].id,
            filepath="attack_patterns.json",
            content='{"patterns": ["SQL Injection", "XSS"]}',
            status=FileStatus.PROCESSED,
            data={"source": "OWASP"},
        ),
    ]

    session.add_all(files)
    session.commit()
    return files


def test_main():
    with SessionLocal() as session:

        # projects = create_projects(session)
        # files = create_files(session, projects)

        # print("Created Projects:", projects)
        # print("Created Files:", files)

        project = session.query(Project).filter_by(name="AI Research").first()
        print([FileEntry.model_validate(f) for f in project.files])

        file_entry = session.query(File).filter_by(filepath="ai_model.py").first()
        print(ProjectData.model_validate(file_entry.project_ref))

        file_entry = FileEntry.model_validate(file_entry)
        assert len(project.files) == 2
        assert file_entry.project_ref
        if file_entry.type_ != FileType.PYTHON:
            raise AssertionError(f"{file_entry.type_} != {FileType.PYTHON}")
        #  cleanup
        # project2 = (
        #     session.query(Project).filter_by(name="Cybersecurity Analysis 2").first()
        # )
        # session.delete(project)
        # session.delete(project2)
        # session.commit()


if __name__ == "__main__":
    test_main()
