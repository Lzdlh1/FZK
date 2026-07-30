"""TestClient 冒烟:健康检查 + 鉴权拦截。

环境无 PostgreSQL/MinIO 时,lifespan 内部 try/except 会跳过初始化,应用仍可启动。
GET /api/parse-jobs 在无 token 时应被 oauth2_scheme 拦截返回 401(不触达 DB)。
"""

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    with TestClient(app) as client:
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_parse_jobs_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/api/parse-jobs")
        assert resp.status_code == 401
