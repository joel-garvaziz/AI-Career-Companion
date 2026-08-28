from fastapi import APIRouter
from app.models.schemas import StudentProfileCreate

router = APIRouter(
    prefix="/profiles",
    tags=["Student Profiles"]
)


@router.post("/")
def create_profile(profile: StudentProfileCreate):

    return {
        "message": "Student profile created successfully",
        "profile": profile
    }