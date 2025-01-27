from fastapi import APIRouter, Request
from src.huggingface.download import HuggingFaceFetchMetadata
from src.huggingface.installer import HuggingFaceInstaller
from pathlib import Path
from uuid import uuid4
import asyncio
from sse_starlette.sse import EventSourceResponse
from fastapi_events.handlers.local import local_handler
import json
from fastapi_events.dispatcher import dispatch
from src.events.events import ModelDownloadProgressEvent, ModelDownloadCompleteEvent, ModelDownloadStartedEvent

router = APIRouter(
    tags=["Model Install"]
)

jobs = {}  # Tracks job progress
tasks = {}  # Tracks active tasks
event_streams = []

@router.get("/huggingface")
async def install_from_hf(model_id: str, download_dir: str = "./models"):
    job_id = str(uuid4())
    dwnld_dir = Path(download_dir)

    # Initialize job progress
    jobs[job_id] = {"progress": 0, "model_id": model_id, "download_path": str(dwnld_dir)}

    # Create installer and start the download task
    installer = HuggingFaceInstaller(dwnld_dir)
    task = asyncio.create_task(installer.install_model(model_id))
    
    # Track the task
    tasks[job_id] = task

    return {"job_id": job_id}


@router.get("/task-status/{job_id}")
async def get_task_status(job_id: str):
    if job_id not in tasks:
        return {"error": "Job not found"}

    task = tasks[job_id]
    if task.done():
        if task.exception():
            return {"status": "failed", "error": str(task.exception())}
        else:
            return {"status": "completed", "result": "Installation successful"}
    else:
        return {"status": "in_progress", "progress": jobs[job_id].get("progress", 0)}
 