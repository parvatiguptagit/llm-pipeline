import subprocess

from fastapi import FastAPI, Request

app = FastAPI()


@app.post("/labelstudio/webhook")
async def labelstudio_webhook(request: Request):
    payload = await request.json()
    print(f"Received webhook: {payload.get('action', 'unknown')}")

    subprocess.Popen(["python", "training_trigger.py"])

    return {"status": "training started"}
