import requests
import threading
from pathlib import Path
from tqdm import tqdm
from typing import Optional, List, Dict
from src.huggingface.schemas import RemoteModelFile
from src.huggingface.download import HuggingFaceFetchMetadata

class HuggingFaceInstaller:
    def __init__(self, download_dir: Path) -> None:
        self.download_dir = download_dir
        self.download_threads: List[threading.Thread] = []
        self.errors: List[Exception] = []
        self._lock = threading.Lock()
        self.progress_bars: Dict[str, tqdm] = {}
        
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
                    position=len(self.progress_bars) + 1  # +1 for total progress bar
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
            
            with self._lock:
                file_progress.close()
                
        except Exception as e:
            with self._lock:
                self.errors.append(e)
                print(f"\nError downloading {file.path}: {str(e)}")
                        
    def install_model(self, model_id: str, variant: Optional[str] = None, max_workers: int = 4) -> None:
        self.download_threads = []
        self.errors = []
        self.progress_bars = {}
        
        fetcher = HuggingFaceFetchMetadata()
        metadata = fetcher.from_id(model_id, variant)
        
        total_size = sum(file.size for file in metadata.files)
        
        print(f"\nStarting download of {len(metadata.files)} files ({total_size / 1024 / 1024:.2f} MB)")
        
        with tqdm(
            total=total_size,
            unit='B',
            unit_scale=True,
            desc=f"Total Progress",
            position=0,
            leave=True
        ) as total_pbar:
            
            for file in metadata.files:
                while len(threading.enumerate()) >= max_workers + 1:
                    continue
                    
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
            
        print(f"Successfully installed {metadata.name} to {self.download_dir}")