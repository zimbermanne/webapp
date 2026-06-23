from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base
from routers import auth, inventory, sales, purchases, expenses, reports, users, backup, activity


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: Close database connections
    engine.dispose()


app = FastAPI(
    title="Shop Management & Accounting System API",
    description="API for managing shop inventory, sales, purchases, expenses, and financial reports",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(sales.router, prefix="/api/sales", tags=["Sales"])
app.include_router(purchases.router, prefix="/api/purchases", tags=["Purchases"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(backup.router, prefix="/api/backup", tags=["Backup"])
app.include_router(activity.router, prefix="/api/activity", tags=["Activity Log"])


@app.get("/")
async def root():
    return {
        "message": "Shop Management & Accounting System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


# Mount static files for the frontend
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """Serve the frontend"""
    from fastapi.responses import FileResponse
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
