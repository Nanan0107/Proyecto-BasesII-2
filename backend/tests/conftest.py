import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import solr  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def cliente() -> TestClient:
    estado = solr.ping()
    if not estado["ok"]:
        pytest.skip(f"Solr no está disponible en {estado['url']}: levántelo e indexe los datos primero.")
    return TestClient(app)


@pytest.fixture(scope="session")
def total(cliente) -> int:
    return cliente.get("/api/estado").json()["documentos"]


def responder(r):
    """Devuelve el JSON o salta la prueba si la consulta aún no está hecha."""
    if r.status_code == 501:
        pytest.skip("pendiente de implementar")
    assert r.status_code == 200, r.json()
    return r.json()
