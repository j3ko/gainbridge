from fastapi import APIRouter, HTTPException

from app.api.deps import SessionDep
from app.models import Job, JobCreate, JobLog, JobPublic
from app.services.jobs import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobPublic)
def create_job(session: SessionDep, body: JobCreate) -> Job | None:
    try:
        return job_manager.create_job(session, body)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/", response_model=list[JobPublic])
def list_jobs(session: SessionDep) -> list[Job]:
    return job_manager.list_jobs(session)


@router.get("/log", response_model=JobLog)
def get_jobs_log(job_id: str | None = None) -> JobLog:
    return JobLog(log=job_manager.read_log(job_id))


@router.get("/{job_id}", response_model=JobPublic)
def get_job(session: SessionDep, job_id: str) -> Job:
    job = job_manager.get_job(session, job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobPublic)
def cancel_job(session: SessionDep, job_id: str) -> Job:
    try:
        job = job_manager.cancel_job(session, job_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not job:
        raise HTTPException(404, "Job not found")
    return job
