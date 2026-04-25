from fastapi.applications import FastAPI

from src.bootstrap.web import create_app

app: FastAPI = create_app()
