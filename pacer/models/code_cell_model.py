from enum import StrEnum, auto
from typing import Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from pacer.models.project_model import ProjectData
from pacer.orm.jupyter_cell_orm import CellType


class CellType(StrEnum):
    PYTHON: str = auto()
    MARKDOWN: str = auto()
    OUTPUT: str = auto()


class Cell(BaseModel):
    """Jupyter notebook cell Basclass"""

    id: UUID = Field(default_factory=uuid4)
    type: CellType = Field(CellType.PYTHON)
    project_ref: ProjectData = Field(default=None, repr=False)
    content: str

    class Config:
        from_attributes = True  # Enable ORM support


class JupyterCells(BaseModel):
    cells: list[Cell]


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
