def test_register_new_user(client):
    r = client.post("/api/auth/register", json={"email": "alice@example.com", "password": "password123"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_duplicate_email_rejected(client):
    client.post("/api/auth/register", json={"email": "bob@example.com", "password": "password123"})
    r = client.post("/api/auth/register", json={"email": "bob@example.com", "password": "password123"})
    assert r.status_code == 409


def test_login_success(client):
    client.post("/api/auth/register", json={"email": "carol@example.com", "password": "password123"})
    r = client.post("/api/auth/login", json={"email": "carol@example.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "dave@example.com", "password": "password123"})
    r = client.post("/api/auth/login", json={"email": "dave@example.com", "password": "wrong-password"})
    assert r.status_code == 401


def test_protected_endpoint_requires_auth(client):
    r = client.get("/api/jobs")
    assert r.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    r = client.get("/api/jobs", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401
