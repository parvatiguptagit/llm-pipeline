"""Shared Label Studio helpers (token or cookie login)."""
import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("LABEL_STUDIO_URL", "https://beta-label.kantham.ai").rstrip("/")
USERNAME = os.getenv("LABEL_STUDIO_EMAIL")
PASSWORD = os.getenv("LABEL_STUDIO_PASSWORD")
API_KEY = os.getenv("LABEL_STUDIO_API_KEY", "").strip()
PROJECT_FILE = "project_id.txt"

LABEL_CONFIG = """
<View>
  <Text name="query" value="$query"/>
  <Text name="code" value="$code"/>
  <Choices name="label" toName="code">
    <Choice value="Relevant"/>
    <Choice value="Not Relevant"/>
  </Choices>
</View>
"""


def load_project_id():
    if os.path.exists(PROJECT_FILE):
        with open(PROJECT_FILE, "r", encoding="utf-8") as f:
            value = f.read().strip()
            if value:
                return int(value)
    return None


def save_project_id(pid):
    with open(PROJECT_FILE, "w", encoding="utf-8") as f:
        f.write(str(pid))


def _is_jwt_token(token: str) -> bool:
    return token.startswith("eyJ") and token.count(".") >= 2


def _cookie_login(session):
    if not USERNAME or not PASSWORD:
        raise RuntimeError(
            "Set LABEL_STUDIO_EMAIL and LABEL_STUDIO_PASSWORD in .env "
            "(JWT personal access tokens on Label Studio 1.23+ require cookie login)."
        )

    session.get(f"{BASE_URL}/user/login/", timeout=60)
    csrftoken = session.cookies.get("csrftoken")
    headers = {"X-CSRFToken": csrftoken, "Referer": f"{BASE_URL}/user/login/"}
    login_res = session.post(
        f"{BASE_URL}/user/login/",
        data={"email": USERNAME, "password": PASSWORD},
        headers=headers,
        timeout=60,
        allow_redirects=True,
    )
    if login_res.status_code not in (200, 302):
        raise RuntimeError(f"Label Studio login failed ({login_res.status_code})")

    csrftoken = session.cookies.get("csrftoken") or csrftoken
    return csrftoken


def login_session():
    session = requests.Session()

    # Legacy non-JWT API keys (Token scheme)
    if API_KEY and not _is_jwt_token(API_KEY):
        return session, ""

    # Label Studio 1.23 JWT "Personal Access Token" + cookie session auth
    csrftoken = _cookie_login(session)
    return session, csrftoken


def api_headers(csrftoken):
    headers = {"Content-Type": "application/json"}
    if API_KEY and not _is_jwt_token(API_KEY):
        headers["Authorization"] = f"Token {API_KEY}"
        return headers
    if csrftoken:
        headers["X-CSRFToken"] = csrftoken
        headers["Referer"] = BASE_URL
    return headers


def parse_results(payload):
    """Handle list or paginated object payloads."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("tasks", "results", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    return []


def ensure_project(session, csrftoken, title="Code Retrieval Dataset"):
    project_id = load_project_id()
    headers = api_headers(csrftoken)

    if project_id:
        url = f"{BASE_URL}/api/projects/{project_id}/"
        res = session.get(url, headers=headers, timeout=60)
        if res.status_code == 200:
            print(f"Using existing project: {project_id}")
            return project_id

    print("Creating Label Studio project...")
    res = session.post(
        f"{BASE_URL}/api/projects/",
        json={"title": title, "label_config": LABEL_CONFIG},
        headers=headers,
        timeout=60,
    )
    res.raise_for_status()
    project_id = res.json()["id"]
    save_project_id(project_id)
    print(f"Project ID: {project_id}")
    return project_id


def delete_project(session, csrftoken, project_id):
    headers = api_headers(csrftoken)
    res = session.delete(f"{BASE_URL}/api/projects/{project_id}/", headers=headers, timeout=60)
    print(f"Deleted project {project_id} (status {res.status_code})")
