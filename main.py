from contextlib import asynccontextmanager
from fastapi import FastAPI
from database import create_tables


from routes.orders import router as orders_router
from routes.stats import router as stats_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    print("Database tables created.")
    yield
    print("Application shutdown.")


app = FastAPI(
    title="Dabbawala Delivery Application",
    description="API for managing dabbawala deliveries and tracking order.",
    version="1.0.0",
    lifespan=lifespan
)

app.include_router(orders_router)
app.include_router(stats_router)


@app.get("/health",tags=["health"])
def health_check():
    return {"status": "ok"}