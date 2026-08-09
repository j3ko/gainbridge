from fastapi import APIRouter, HTTPException
from app.api.deps import SessionDep
from app.models import JobCreate, JobPublic
from app.services.jobs import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobPublic)
def create_job(session: SessionDep, body: JobCreate):
    try:
        return job_manager.create_job(session, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/", response_model=list[JobPublic])
def list_jobs(session: SessionDep):
    return job_manager.list_jobs(session)


@router.get("/{job_id}", response_model=JobPublic)
def get_job(session: SessionDep, job_id: str):
    job = job_manager.get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job