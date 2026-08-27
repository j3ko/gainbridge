from fastapi.routing import APIRoute
from starlette.middleware.cors import CORSMiddleware

from app.main import app, custom_generate_unique_id


def test_health_check(client):
    response = client.get("/api/v1/utils/health-check/")
    assert response.status_code == 200
    assert response.json() is True


def test_custom_generate_unique_id_uses_first_tag_and_route_name():
    route = APIRoute(
        "/utils/health-check/",
        endpoint=lambda: True,
        tags=["utils"],
        name="health_check",
    )
    assert custom_generate_unique_id(route) == "utils-health_check"


def test_cors_middleware_is_registered():
    assert any(m.cls is CORSMiddleware for m in app.user_middleware)
