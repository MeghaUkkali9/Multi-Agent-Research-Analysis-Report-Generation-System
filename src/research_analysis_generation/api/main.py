import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from research_analysis_generation.api.route.report_route import router
from datetime import datetime

app = FastAPI(title="Autonomous Report Generator UI")
from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parents[1]  # adjust if needed

# STATIC_DIR = BASE_DIR / "src" / "static"

# print("Static directory:", STATIC_DIR)

# app.mount(
#     "/static",
#     StaticFiles(directory=str(STATIC_DIR)),
#     name="static"
# )

import os

print("\n\n\n\ncwd =", os.getcwd())
print("static exists =", os.path.exists("src/static"))
app.mount(
    "/static",
    StaticFiles(directory="src/static"),
    name="static"
)
templates = Jinja2Templates(directory="src/research_analysis_generation/api/templates")
app.templates = templates  # so templates accessible inside router

# 🔹 ADD THIS FUNCTION
def basename_filter(path: str):
    return os.path.basename(path)

# 🔹 REGISTER FILTER
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