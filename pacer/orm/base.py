import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_PATH = Path(__file__).parent / ".pacer.db"

Base = declarative_base()


@lru_cache(1)
def make_session(db_path: Path = DB_PATH):
    """Create a `Session` class (not the object)"""
    from pacer.orm import file_orm, project_orm

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)
    return Session
