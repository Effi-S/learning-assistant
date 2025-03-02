from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pacer.models.project_model import ProjectData


class Code(BaseModel):
    """Jupter notebook cell for learning"""

    id: UUID = None
    language: str = Field("python")
    markdown: str = Field("Markdow explanation of the code.", description="")
    code: str = Field("The code example itself.")
    output: str = Field("The expected output")
    project_ref: ProjectData = Field(default=None, repr=False)

    class Config:
        from_attributes = True  # Enable ORM support


class CodeCells:
    cells: list[Code]


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
