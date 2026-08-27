def _create_source(client, name="lib"):
    response = client.post(
        "/api/v1/sources/",
        json={"name": name, "type": "plex", "base_url": "http://x", "token": "t"},
    )
    assert response.status_code == 200


def test_create_job(client):
    _create_source(client)
    response = client.post("/api/v1/jobs/", json={"source_name": "lib"})
    assert response.status_code == 200
    body = response.json()
    assert body["source_name"] == "lib"
    assert body["status"] == "pending"


def test_create_job_unknown_source(client):
    response = client.post("/api/v1/jobs/", json={"source_name": "missing"})
    assert response.status_code == 400


def test_create_job_conflict_when_already_running(client):
    _create_source(client)
    first = client.post("/api/v1/jobs/", json={"source_name": "lib"})
    assert first.status_code == 200
    second = client.post("/api/v1/jobs/", json={"source_name": "lib"})
    assert second.status_code == 409


def test_list_jobs(client):
    _create_source(client)
    client.post("/api/v1/jobs/", json={"source_name": "lib"})
    response = client.get("/api/v1/jobs/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert len(body["data"]) == 1


def test_list_jobs_pagination_params(client):
    response = client.get("/api/v1/jobs/?skip=0&limit=10")
    assert response.status_code == 200
    assert response.json() == {"data": [], "count": 0}


def test_get_job(client):
    _create_source(client)
    created = client.post("/api/v1/jobs/", json={"source_name": "lib"}).json()
    response = client.get(f"/api/v1/jobs/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_job_not_found(client):
    response = client.get("/api/v1/jobs/missing")
    assert response.status_code == 404


def test_cancel_job(client):
    _create_source(client)
    created = client.post("/api/v1/jobs/", json={"source_name": "lib"}).json()
    response = client.post(f"/api/v1/jobs/{created['id']}/cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_job_not_found(client):
    response = client.post("/api/v1/jobs/missing/cancel")
    assert response.status_code == 404


def test_cancel_job_not_running(client):
    _create_source(client)
    created = client.post("/api/v1/jobs/", json={"source_name": "lib"}).json()
    client.post(f"/api/v1/jobs/{created['id']}/cancel")
    response = client.post(f"/api/v1/jobs/{created['id']}/cancel")
    assert response.status_code == 400


def test_get_jobs_log(client):
    response = client.get("/api/v1/jobs/log")
    assert response.status_code == 200
    assert isinstance(response.json()["log"], str)


def test_get_jobs_log_filtered_by_job_id(client):
    response = client.get("/api/v1/jobs/log?job_id=no-such-job-id-xyz")
    assert response.status_code == 200
    assert response.json()["log"] == ""
