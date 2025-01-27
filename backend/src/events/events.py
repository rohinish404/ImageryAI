from fastapi_events.registry.payload_schema import registry as payload_schema
from pydantic import BaseModel, Field

@payload_schema.register
class ModelDownloadStartedEvent(BaseModel):
    """Event model for model_download_started"""

    __event_name__ = "model_download_started"

    model_id: str = Field(description="The ID of the model being downloaded")
    download_path: str = Field(description="The local path where the download is saved")

    @classmethod
    def build(cls, model_id: str, download_path: str) -> "ModelDownloadStartedEvent":
        return cls(model_id=model_id, download_path=download_path)


@payload_schema.register
class ModelDownloadProgressEvent(BaseModel):
    """Event model for model_download_progress"""

    __event_name__ = "model_download_progress"

    model_id: str = Field(description="The ID of the model being downloaded")
    download_path: str = Field(description="The local path where the download is saved")
    current_bytes: int = Field(description="The number of bytes downloaded so far")
    total_bytes: int = Field(description="The total number of bytes to be downloaded")
    progress_percentage: float = Field(description="The percentage of the download completed")

    @classmethod
    def build(cls, model_id: str, download_path: str, current_bytes: int, total_bytes: int) -> "ModelDownloadProgressEvent":
        progress_percentage = int((current_bytes / total_bytes) * 100)
        return cls(
            model_id=model_id,
            download_path=download_path,
            current_bytes=current_bytes,
            total_bytes=total_bytes,
            progress_percentage=progress_percentage
        )


@payload_schema.register
class ModelDownloadCompleteEvent(BaseModel):
    """Event model for model_download_complete"""

    __event_name__ = "model_download_complete"

    model_id: str = Field(description="The ID of the model being downloaded")
    download_path: str = Field(description="The local path where the download is saved")
    total_bytes: int = Field(description="The total number of bytes downloaded")

    @classmethod
    def build(cls, model_id: str, download_path: str, total_bytes: int) -> "ModelDownloadCompleteEvent":
        return cls(model_id=model_id, download_path=download_path, total_bytes=total_bytes)