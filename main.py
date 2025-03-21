import uvicorn
from fastapi import FastAPI
from database import engine
from models import Base
from routes import links, users, admin
from background_cleanup import scheduler
from prometheus_fastapi_instrumentator import Instrumentator
import asyncio

app = FastAPI(title="Link Shortener API")

app.include_router(users.router)
app.include_router(links.router)
app.include_router(admin.router)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Link Shortener API!"}

Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
async def on_startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    asyncio.create_task(scheduler())

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)