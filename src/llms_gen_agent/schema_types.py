""" Define types used for schema validation for model input and output. """
from pydantic import BaseModel, Field


class SummaryOutput(BaseModel):
    file_path: str = Field(description="The path to the document.")
    summary: str = Field(description="A summary of of the document.")

class DocumentSummariesOutput(BaseModel):
    summaries: dict[str, str] = Field(
        description="A dictionary where keys are file paths and values are their summaries."
    )
