from fastapi import APIRouter
from src.huggingface.download import HuggingFaceFetchMetadata
from src.huggingface.installer import HuggingFaceInstaller
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from src.tasks import install_model_task
from celery.result import AsyncResult
from uuid import uuid4
import asyncio 
from sse_starlette.sse import EventSourceResponse
from fastapi_events.handlers.local import local_handler

router = APIRouter(
    tags=["Model Install"]
)

jobs = {}
tasks = {} 

@router.get("/huggingface")
async def install_from_hf(model_id: str, download_dir: str = "./models"):
    job_id = str(uuid4())
    dwnld_dir = Path(download_dir)

    jobs[job_id] = {"progress": 0, "model_id": model_id}

    installer = HuggingFaceInstaller(dwnld_dir)
    task = asyncio.create_task(installer.install_model(model_id))
    
    tasks[job_id] = task

    return {"job_id": job_id}

@router.get("/stream/{job_id}")
async def stream_events(job_id: str):
    async def event_generator():
        while True:
            if job_id not in jobs:
                yield {"event": "error", "data": "Job not found"}
                break

            job_status = jobs[job_id]
            if job_status.get("progress") == 100:
                yield {"event": "complete", "data": "Installation complete"}
                break

            yield {"event": "progress", "data": job_status.get("progress", 0)}
            await asyncio.sleep(1) 

    return EventSourceResponse(event_generator())

@router.get("/task-status/{job_id}")
async def get_task_status(job_id: str):
    if job_id not in tasks:
        return {"error": "Job not found"}

    task = tasks[job_id]
    if task.done():
        if task.exception():
            return {"status": "failed", "error": str(task.exception())}
        else:
            return {"status": "completed", "result": task.result()}
    else:
        return {"status": "in_progress"}

@local_handler.register(event_name="model_download_started")
async def handle_download_start(event):
    event_name, payload = event 
    model_id = payload["model_id"]
    download_path = payload["download_path"]
    
    jobs[model_id] = {"progress": 0, "download_path": download_path}
    print(f"Download started for model {model_id} at {download_path}")

@local_handler.register(event_name="model_download_progress")
async def handle_download_progress(event):
    event_name, payload = event 
    model_id = payload["model_id"]
    current_bytes = payload["current_bytes"]
    total_bytes = payload["total_bytes"]
    progress_percentage = (current_bytes / total_bytes) * 100

    jobs[model_id]["progress"] = progress_percentage
    print(f"Progress for model {model_id}: {progress_percentage}%")

@local_handler.register(event_name="model_download_complete")
async def handle_download_complete(event):
    event_name, payload = event 
    model_id = payload["model_id"]
    total_bytes = payload["total_bytes"]

    jobs[model_id]["progress"] = 100
    print(f"Download completed for model {model_id}. Total bytes: {total_bytes}")