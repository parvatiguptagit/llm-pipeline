import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from label_studio_client import BASE_URL, api_headers, load_project_id, login_session


def export_labels():
    project_id = load_project_id()
    if not project_id:
        raise FileNotFoundError("project_id.txt missing. Run pipeline.py upload step first.")

    session, csrftoken = login_session()
    url = f"{BASE_URL}/api/projects/{project_id}/export?exportType=JSON"
    res = session.get(url, headers=api_headers(csrftoken), timeout=300)
    res.raise_for_status()

    with open("labelstudio_export.json", "w", encoding="utf-8") as f:
        f.write(res.text)

    print("Labels exported")


if __name__ == "__main__":
    export_labels()
