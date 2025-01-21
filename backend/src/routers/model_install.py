from fastapi import APIRouter
from src.huggingface.download import HuggingFaceFetchMetadata
from src.huggingface.installer import HuggingFaceInstaller
from pathlib import Path
router = APIRouter(
    tags=["Model Install"]
)


@router.get("/huggingface")
async def install_from_hf(id: str, download_dir: str ):
    dwnld_dir = Path(download_dir)
# "./models"
    installer = HuggingFaceInstaller(dwnld_dir)
    installer.install_model(id, max_workers=4)
    # metadata = HuggingFaceFetchMetadata().from_id(id=id)
    return None
