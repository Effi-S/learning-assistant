from enum import StrEnum, auto
from typing import Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer

from pacer.models.project_model import ProjectData


class CellType(StrEnum):
    PYTHON: str = auto()
    CODE: str = auto()
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

    @field_serializer("type")
    def serialize_type(self, value: CellType, _info) -> str:
        return value.value


class JupyterCells(BaseModel):
    cells: list[Cell]

    @classmethod
    def from_nodes(cls, nodes):
        cells = [Cell(type=n.cell_type, content=n.source) for n in nodes]
        return cls(cells=cells)


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
