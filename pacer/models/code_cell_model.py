from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator

from pacer.models.project_model import ProjectData


class Code(BaseModel):
    """Jupter notebook cell for learning"""

    id: UUID = Field(default_factory=uuid4)
    language: str = Field("python")
    markdown: str = Field("", description="Markdown explanation of the code.")
    code: str = Field("", description="The code example itself.")
    output: str = Field("", description="The expected output")
    project_ref: ProjectData = Field(default=None, repr=False)

    class Config:
        from_attributes = True  # Enable ORM support


class CodeCells:
    cells: list[Code]


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
