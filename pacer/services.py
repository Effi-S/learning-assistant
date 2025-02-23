from uuid import uuid4

from sqlalchemy.orm import Session

from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm import base
from pacer.orm.file_orm import File, FileStatus
from pacer.orm.project_orm import Project

SessionLocal = base.make_session()


# Creating two projects
def create_projects(session: Session):
    project1 = Project(
        id=str(uuid4()), name="AI Research", data={"category": "Machine Learning"}
    )
    project2 = Project(
        id=str(uuid4()), name="Cybersecurity Analysis", data={"category": "Security"}
    )

    session.add_all([project1, project2])
    session.commit()
    return project1, project2


def create_files(session: Session, projects):
    files = [
        File(
            id=str(uuid4()),
            project_id=projects[0].id,  # Assigning to Project 1
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
            project_id=projects[1].id,  # Assigning to Project 2
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


def main():
    with SessionLocal() as session:

        projects = create_projects(session)
        files = create_files(session, projects)

        # print("Created Projects:", projects)
        # print("Created Files:", files)

        project = session.query(Project).filter_by(name="AI Research").first()
        print(project.files)  # List of FileEntry objects

        file_entry = session.query(File).filter_by(filepath="ai_model.py").first()
        print(file_entry.project_ref)  # Project object


if __name__ == "__main__":
    main()
