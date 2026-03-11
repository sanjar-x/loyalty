from fastapi.applications import FastAPI

from src.bootstrap.app import create_app

app: FastAPI = create_app()
