import requests
import threading
from pathlib import Path
from tqdm import tqdm
from typing import Optional, List, Dict
from fastapi_events.dispatcher import dispatch
from src.huggingface.schemas import RemoteModelFile
from src.huggingface.download import HuggingFaceFetchMetadata
from src.events.events import ModelDownloadCompleteEvent, ModelDownloadProgressEvent, ModelDownloadStartedEvent
import asyncio

class HuggingFaceInstaller:
    def __init__(self, download_dir: Path) -> None:
        self.download_dir = download_dir
        self.download_threads: List[threading.Thread] = []
        self.errors: List[Exception] = []
        self._lock = threading.Lock()
        self.progress_bars: Dict[str, tqdm] = {}
        self.total_bytes_downloaded: int = 0
        self.total_size: int = 0
        
    def download_file(self, file: RemoteModelFile, total_progress: tqdm) -> None:
        try:
            file_path = self.download_dir / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with self._lock:
                file_progress = tqdm(
                    total=file.size,
                    unit='B',
                    unit_scale=True,
                    desc=f"File: {file.path.name}",
                    leave=True,
                    position=len(self.progress_bars) + 1  
                )
                self.progress_bars[str(file.path)] = file_progress
                
            response = requests.get(file.url, stream=True)
            response.raise_for_status()
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        with self._lock:
                            file_progress.update(len(chunk))
                            total_progress.update(len(chunk))
                            self.total_bytes_downloaded += len(chunk)
                            self._dispatch_progress_event()
            
            with self._lock:
                file_progress.close()
                
        except Exception as e:
            with self._lock:
                self.errors.append(e)
                print(f"\nError downloading {file.path}: {str(e)}")
    
    def _dispatch_progress_event(self):
        progress_percentage = (self.total_bytes_downloaded / self.total_size) * 100
        if progress_percentage % 1 == 0:
            dispatch(
                ModelDownloadProgressEvent.build(
                    model_id=self.model_id,
                    download_path=str(self.download_dir),
                    current_bytes=self.total_bytes_downloaded,
                    total_bytes=self.total_size
                )
            )
                        
    async def install_model(self, model_id: str, variant: Optional[str] = None, max_workers: int = 4) -> None:
        self.download_threads = []
        self.errors = []
        self.progress_bars = {}
        self.total_bytes_downloaded = 0
        self.model_id = model_id
        
        fetcher = HuggingFaceFetchMetadata()
        metadata = fetcher.from_id(model_id, variant)
        
        self.total_size = sum(file.size for file in metadata.files)

        print(f"\nStarting download of {len(metadata.files)} files ({self.total_size / 1024 / 1024:.2f} MB)")

        dispatch(
            ModelDownloadStartedEvent.build(
                model_id=model_id,
                download_path=str(self.download_dir)
            )
        )
        
        with tqdm(
            total=self.total_size,
            unit='B',
            unit_scale=True,
            desc=f"Total Progress",
            position=0,
            leave=True
        ) as total_pbar:
            
            for file in metadata.files:
                while len(threading.enumerate()) >= max_workers + 1:
                    await asyncio.sleep(0.1) 
                    
                thread = threading.Thread(
                    target=self.download_file,
                    args=(file, total_pbar),
                    daemon=True
                )
                self.download_threads.append(thread)
                thread.start()
            
            for thread in self.download_threads:
                thread.join()
        
        print("\n" * (len(metadata.files) + 1))
        
        if self.errors:
            raise Exception(f"Encountered {len(self.errors)} errors during download: {self.errors}")

        dispatch(
            ModelDownloadCompleteEvent.build(
                model_id=model_id,
                download_path=str(self.download_dir),
                total_bytes=self.total_size
            )
        )
            
        print(f"Successfully installed {metadata.name} to {self.download_dir}")