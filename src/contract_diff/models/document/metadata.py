from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class DocumentMetadata(BaseModel):
    """
    Metadata discovered directly from the document.
    """

    model_config = ConfigDict(frozen=True)

    filename: str

    extension: str

    size_bytes: int

    title: str | None = None

    author: str | None = None

    creator: str | None = None

    producer: str | None = None

    creation_date: datetime | None = None

    modification_date: datetime | None = None

    page_count: int | None = None

    @property
    def stem(self) -> str:
        """
        Filename without extension.
        """
        return Path(self.filename).stem
