from fastapi.applications import FastAPI

from src.bootstrap.web import create_app

app: FastAPI = create_app()
# claude --resume 5043b823-156f-4344-ad44-5b109dd61da4
