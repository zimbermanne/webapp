from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base
from routers import auth, inventory, sales, purchases, expenses, reports, users, backup, activity

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()

app = FastAPI(
    title="Shop Management & Accounting System API",
    description="API for managing shop inventory, sales, purchases, expenses, and financial reports",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(inventory.router, prefix="/api/inventory", tags=["Inventory"])
app.include_router(sales.router, prefix="/api/sales", tags=["Sales"])
app.include_router(purchases.router, prefix="/api/purchases", tags=["Purchases"])
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(backup.router, prefix="/api/backup", tags=["Backup"])
app.include_router(activity.router, prefix="/api/activity", tags=["Activity Log"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

# 1. Mount the static folder so browser can load /static/styles.css and /static/app.js
# HTML paths inside index.html should look like: /static/styles.css and /static/app.js
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. Serve the index.html directly on the root URL
@app.get("/")
async def serve_root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend static index.html build missing inside static/ directory."}

# 3. Catch-all route for Single Page Application (SPA) routing navigation
@app.get("/{catchall:path}")
async def serve_frontend(catchall: str):
    if catchall.startswith("api/"):
        return {"detail": "Not Found"}, 404
    
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"detail": "Not Found"}
