from fastapi import APIRouter, HTTPException, Query

from app.api.deps import SessionDep
from app.models import Job, JobCreate, JobLog, JobPublic, JobsPublic
from app.services.jobs import job_manager

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=JobPublic)
def create_job(session: SessionDep, body: JobCreate) -> Job:
    try:
        job = job_manager.create_job(session, body, skip_if_running=True)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if job is None:
        raise HTTPException(409, f'A sync is already running for "{body.source_name}"')
    return job


@router.get("/", response_model=JobsPublic)
def list_jobs(
    session: SessionDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
) -> JobsPublic:
    jobs, count = job_manager.list_jobs(session, skip=skip, limit=limit)
    return JobsPublic(data=jobs, count=count)


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
