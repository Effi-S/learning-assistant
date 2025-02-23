from uuid import uuid4

from sqlalchemy.orm import Session

from pacer.models.file_model import FileEntry
from pacer.models.project_model import ProjectData
from pacer.orm import base
from pacer.orm.file_orm import File, FileStatus
from pacer.orm.project_orm import Project

SessionLocal = base.make_session()
