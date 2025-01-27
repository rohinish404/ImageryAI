import aiohttp
import asyncio
from pathlib import Path
from tqdm import tqdm
from typing import Optional, Dict, List
from fastapi_events.dispatcher import dispatch
from src.huggingface.schemas import RemoteModelFile
from src.huggingface.download import HuggingFaceFetchMetadata
from src.events.events import ModelDownloadCompleteEvent, ModelDownloadProgressEvent, ModelDownloadStartedEvent

class HuggingFaceInstaller:
    def __init__(self, download_dir: Path) -> None:
        self.download_dir = download_dir
        self.errors: List[Exception] = []
        self.progress_bars: Dict[str, tqdm] = {}
        self.total_bytes_downloaded: int = 0
        self.total_size: int = 0
        self.last_reported_bytes: int = 0

    async def download_file(self, file: RemoteModelFile, total_progress: tqdm) -> None:
        from main import event_handler_id
        try:
            file_path = self.download_dir / file.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_progress = tqdm(
                total=file.size,
                unit='B',
                unit_scale=True,
                desc=f"File: {file.path.name}",
                leave=True,
                position=len(self.progress_bars) + 1  
            )
            self.progress_bars[str(file.path)] = file_progress

            async with aiohttp.ClientSession() as session:

                response = await session.get(str(file.url))

                if not response.ok:
                    print("not")
                    
                with open(file_path, 'wb') as f:
                    
                    while True:
                        chunk = await response.content.read(10000)
                        if not chunk:
                            break
                        f.write(chunk)
                        file_progress.update(len(chunk))
                        total_progress.update(len(chunk))
                        self.total_bytes_downloaded += len(chunk)

                        if (self.total_bytes_downloaded - self.last_reported_bytes >= (self.total_size / 100)) or (self.total_bytes_downloaded >= self.total_size):
                            print(f"progress percentage - {int((self.total_bytes_downloaded / self.total_size) * 100)}")
                            self.last_reported_bytes = self.total_bytes_downloaded

                            print(f"\Progress Event Handler ID: {event_handler_id}")

                            try:
                                progress_event = ModelDownloadProgressEvent.build(
                                    model_id=self.model_id,
                                    download_path=str(self.download_dir),
                                    current_bytes=self.total_bytes_downloaded,
                                    total_bytes=self.total_size
                                )
                                await asyncio.sleep(0)
                                dispatch(progress_event, middleware_id=event_handler_id)
                                print(f"Dispatched progress event: {progress_event}")
                            except Exception as e:
                                print(f"error = {e}")             

            file_progress.close()
                
        except Exception as e:
            self.errors.append(e)
            print(f"\nError downloading {file.path}: {str(e)}")

    async def install_model(self, model_id: str, variant: Optional[str] = None) -> None:
        from main import event_handler_id        

        self.errors = []
        self.progress_bars = {}
        self.total_bytes_downloaded = 0
        self.last_reported_bytes = 0
        self.model_id = model_id
        
        fetcher = HuggingFaceFetchMetadata()
        metadata = fetcher.from_id(model_id, variant)
        
        self.total_size = sum(file.size for file in metadata.files)

        print(f"\nStarting download of {len(metadata.files)} files ({self.total_size / 1024 / 1024:.2f} MB)")

        print(f"\nStarted Event Handler ID: {event_handler_id}")

        try:
            dispatch(
                ModelDownloadStartedEvent.build(
                    model_id=model_id,
                    download_path=str(self.download_dir)
                ), middleware_id=event_handler_id
            )
            print("event dispatched")
        except Exception as e:
            print(f"error - {e}")
        with tqdm(
            total=self.total_size,
            unit='B',
            unit_scale=True,
            desc=f"Total Progress",
            position=0,
            leave=True
        ) as total_pbar:
            
            for file in metadata.files:
                await self.download_file(file, total_pbar)
        
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