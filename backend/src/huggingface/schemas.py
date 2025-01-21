from pydantic import BaseModel
from typing import List, Literal, Optional, Union
from pathlib import Path
from pydantic.networks import AnyHttpUrl

class RemoteModelFile(BaseModel):
    url: AnyHttpUrl
    path: Path
    size: Optional[int]
    sha256: Optional[str]

class HuggingFaceMetadata(BaseModel):
            id: str
            name: str
            files: list[RemoteModelFile]
            is_diffusers: bool