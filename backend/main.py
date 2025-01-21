from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routers import model_install
version = 'v1'
app = FastAPI(version=version)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(model_install.router, prefix=f"/api/{version}/model_install")






