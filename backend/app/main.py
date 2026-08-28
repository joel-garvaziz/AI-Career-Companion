from fastapi import FastAPI

from app.api.profile_routes import router as profile_router


app = FastAPI(
    title="AI Career Companion",
    description="AI Career Companion Agent for Internship Matching and Interview Preparation",
    version="1.0.0"
)


app.include_router(profile_router)


@app.get("/")
def home():
    return {
        "message": "AI Career Companion API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }