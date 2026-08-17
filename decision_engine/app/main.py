from fastapi import FastAPI
from .routes import triage, queue, override, reassign, my_queue
from .routes.auth import router as auth_router

app = FastAPI(title="TrustMeBro Engine")

app.include_router(triage.router)
app.include_router(queue.router)
app.include_router(override.router)
app.include_router(reassign.router)
app.include_router(my_queue.router)
app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "decision_engine running"}