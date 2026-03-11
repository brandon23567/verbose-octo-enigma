from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes.code_explainer_routes import router as code_explainer_routes

app = FastAPI(
    title="Code-To-Text",
    description="Get back a description of your code using intelligent ai",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_headers=["*"],
    allow_methods=["*"],
    allow_origins=["*"],
    allow_credentials=True
)

app.include_router(code_explainer_routes)

@app.get("/")
async def home_root():
    return { "message": "Hello brandon" }