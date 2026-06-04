import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from label_studio_client import BASE_URL, api_headers, ensure_project, login_session, parse_results

session, csrf = login_session()
pid = ensure_project(session, csrf)
headers = api_headers(csrf)

tasks, page = [], 1
while True:
    res = session.get(f"{BASE_URL}/api/tasks/?project={pid}&page={page}&page_size=100", headers=headers, timeout=120)
    if res.status_code == 404:
        break
    batch = parse_results(res.json())
    if not batch:
        break
    tasks.extend(batch)
    if len(batch) < 100:
        break
    page += 1

queries  = [t["data"].get("query", "").strip() for t in tasks]
codes    = [t["data"].get("code", "").strip() for t in tasks]

dup_q    = {q: c for q, c in Counter(queries).items() if c > 1 and q}
dup_c    = {c: n for c, n in Counter(codes).items() if n > 1 and c}
garbled  = [t for t in tasks if "as function that" in t["data"].get("query", "").lower()]
no_q     = [t for t in tasks if not t["data"].get("query", "").strip()]
no_code  = [t for t in tasks if not t["data"].get("code", "").strip()]
sig_only = [t for t in tasks if len([l for l in t["data"].get("code", "").strip().splitlines() if l.strip()]) <= 1]

print(f"Total tasks          : {len(tasks)}")
print(f"Duplicate queries    : {len(dup_q)} groups  ({sum(dup_q.values())} tasks)")
print(f"Duplicate code bodies: {len(dup_c)} groups  ({sum(dup_c.values())} tasks)")
print(f"Garbled queries      : {len(garbled)}")
print(f"No query             : {len(no_q)}")
print(f"No code              : {len(no_code)}")
print(f"Signature-only code  : {len(sig_only)}")
print()
if dup_q:
    print("Sample duplicate queries:")
    for q, c in list(dup_q.items())[:5]:
        print(f"  [{c}x] {q[:90]}")
if dup_c:
    print("\nSample duplicate code (first line):")
    for code, n in list(dup_c.items())[:5]:
        print(f"  [{n}x] {code.splitlines()[0][:90]}")
