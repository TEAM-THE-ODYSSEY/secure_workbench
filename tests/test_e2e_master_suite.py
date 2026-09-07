import pytest
import requests

BASE_URL = "http://localhost:8000/api"

def test_health():
    resp = requests.get(f"{BASE_URL}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["ok", "online"]

def test_login_operator():
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "operator", "password": "operator123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "operator"
    return data["access_token"]

def test_login_admin():
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"
    return data["access_token"]

def test_conversations_persistence_and_isolation():
    token_op = test_login_operator()
    headers_op = {"Authorization": f"Bearer {token_op}"}

    # 1. Create conversation as operator
    resp = requests.post(f"{BASE_URL}/v1/conversations", json={"title": "Operator Safety Chat"}, headers=headers_op)
    assert resp.status_code == 201
    conv_data = resp.json()
    conv_id = conv_data["id"]

    # 2. List conversations as operator
    resp_list = requests.get(f"{BASE_URL}/v1/conversations", headers=headers_op)
    assert resp_list.status_code == 200
    user_convs = resp_list.json()
    assert any(c["id"] == conv_id for c in user_convs)

    # 3. Post message in conversation
    msg_resp = requests.post(
        f"{BASE_URL}/v1/conversations/{conv_id}/messages",
        json={"text": "What is the operating vibration limit for P-101A?"},
        headers=headers_op,
    )
    assert msg_resp.status_code == 200
    msg_data = msg_resp.json()
    assert "assistant_message" in msg_data
    assert "vibration" in msg_data["assistant_message"]["text"].lower()

    # 4. User Isolation Check: Admin logs in and tries to access operator's conversation ID directly
    token_admin = test_login_admin()
    headers_admin = {"Authorization": f"Bearer {token_admin}"}
    unauth_resp = requests.get(f"{BASE_URL}/v1/conversations/{conv_id}", headers=headers_admin)
    assert unauth_resp.status_code == 404 # Isolated from other users!

def test_admin_control_plane():
    token_admin = test_login_admin()
    headers = {"Authorization": f"Bearer {token_admin}"}

    # 1. Check Statistics API
    stats_resp = requests.get(f"{BASE_URL}/v1/admin/statistics", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert "total_users" in stats
    assert stats["total_users"] >= 2

    # 2. Check System Health Probe API
    health_resp = requests.get(f"{BASE_URL}/v1/admin/system-health", headers=headers)
    assert health_resp.status_code == 200
    health = health_resp.json()
    assert health["status"] in ["HEALTHY", "WARNING"]
    assert any(c["name"] == "PostgreSQL" and c["status"] == "ONLINE" for c in health["components"])
