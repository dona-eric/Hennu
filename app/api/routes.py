from fastapi import FastAPI
from fastapi import UploadFile, File, Form
from app.RAG.graph import customer_agent



app = FastAPI(
    debug=False,
    title=f"HennuAPI",
    description="API d'automatisation",
    openapi_url="/openai.json",
    docs_url="/docs",
    redoc_url='/redoc', 
)


@app.get()

def agent():
    