from pathlib import Path
from huggingface_hub import HfApi, hf_hub_url
from src.huggingface.schemas import RemoteModelFile, HuggingFaceMetadata

class HuggingFaceFetchMetadata:
    def __init__(self) -> None:
        pass

    def from_id(self, id: str, variant=None):
        model_info = None
        try:
            model_info = HfApi().model_info(repo_id=id, files_metadata=True, revision=variant)
        except Exception as e:
            print(f'caught {type(e): e}: e')

        files: list[RemoteModelFile] = []

        _, name = id.split("/")

        for s in model_info.siblings or []:
            assert s.rfilename is not None
            assert s.size is not None
            files.append(
                RemoteModelFile(
                    url=hf_hub_url(id, s.rfilename, revision=variant or "main"),
                    path=Path(name, s.rfilename),
                    size=s.size,
                    sha256=s.lfs.get("sha256") if s.lfs else None,
                )
            )
        
        is_diffusers = any(str(f.url).endswith(("model_index.json", "config.json")) for f in files)

        return HuggingFaceMetadata(
            id=model_info.id,
            name=name,
            files=files,
            is_diffusers=is_diffusers,
        )
        