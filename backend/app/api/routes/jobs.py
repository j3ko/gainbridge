from fastapi import APIRouter, HTTPException
from app.schemas.gain import JobCreate, JobInfo
from app.services.jobs import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobInfo)
def create_job(body: JobCreate):
    try:
        return job_manager.create_job(body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/", response_model=list[JobInfo])
def list_jobs():
    return job_manager.list_jobs()


@router.get("/{job_id}", response_model=JobInfo)
def get_job(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job