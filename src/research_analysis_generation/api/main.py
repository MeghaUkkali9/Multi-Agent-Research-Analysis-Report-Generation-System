import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from research_analysis_generation.api.route.report_route import router
from datetime import datetime

app = FastAPI(title="Autonomous Report Generator UI")
from pathlib import Path

app.mount(
    "/static",
    StaticFiles(directory="src/static"),
    name="static"
)
templates = Jinja2Templates(directory="src/research_analysis_generation/api/templates")
app.templates = templates  

def basename_filter(path: str):
    return os.path.basename(path)

templates.env.filters["basename"] = basename_filter

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

#health check have been added
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {
        "status": "healthy",
        "service": "research-report-generation",
        "timestamp": datetime.now().isoformat()
    }

# Register Routes
app.include_router(router)