import uvicorn
import logging
from fastapi import FastAPI
from database import engine
from models import Base
from routes import links, users, admin
from background_cleanup import scheduler
from prometheus_fastapi_instrumentator import Instrumentator
import asyncio

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

app = FastAPI(
    title="Link Shortener API",
    root_path="/api",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

app.include_router(users.router)
app.include_router(links.router)
app.include_router(admin.router)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Link Shortener API!"}

Instrumentator().instrument(app).expose(app)

@app.on_event("startup")
async def on_startup():
    for i in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            asyncio.create_task(scheduler())
            break
        except Exception as e:
            print(f"[Startup] DB not ready, retrying in 3s... (attempt {i+1})")
            await asyncio.sleep(3)
    else:
        print("[Startup] Failed to connect to DB after multiple attempts.")
        raise


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)