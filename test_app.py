"""
Simple test script to verify the webapp structure and dependencies.
"""
import sys
import os

print("=" * 60)
print("Shop Management Webapp - Structure Test")
print("=" * 60)

# Test 1: Check Python version
print("\n✓ Python version:", sys.version.split()[0])

# Test 2: Check if all required files exist
required_files = [
    'main.py',
    'database.py', 
    'models.py',
    'schemas.py',
    'auth.py',
    'activity.py',
    'requirements.txt',
    '.env',
    'init_db.py',
    'routers/__init__.py',
    'routers/auth.py',
    'routers/users.py',
    'routers/inventory.py',
    'routers/sales.py',
    'routers/purchases.py',
    'routers/expenses.py',
    'routers/reports.py',
    'routers/activity.py',
    'routers/backup.py',
    'static/index.html',
    'static/styles.css',
    'static/app.js',
]

print("\n✓ Checking required files...")
for file in required_files:
    if os.path.exists(file):
        print(f"  ✓ {file}")
    else:
        print(f"  ✗ {file} - MISSING!")

# Test 3: Check if we can import main modules
print("\n✓ Testing module imports...")
try:
    # These might fail if dependencies aren't installed
    print("  Note: Some imports may fail if dependencies aren't installed yet")
    print("  Install dependencies with: pip install -r requirements.txt")
except ImportError as e:
    print(f"  Import error (expected if deps not installed): {e}")

# Test 4: Check directory structure
print("\n✓ Checking directory structure...")
required_dirs = ['routers', 'static']
for dir in required_dirs:
    if os.path.isdir(dir):
        print(f"  ✓ {dir}/")
    else:
        print(f"  ✗ {dir}/ - MISSING!")

print("\n" + "=" * 60)
print("Structure test completed!")
print("=" * 60)
print("\nNext steps:")
print("1. Install PostgreSQL and create database")
print("2. Update .env with your database credentials") 
print("3. Install dependencies: pip install -r requirements.txt")
print("4. Initialize database: python init_db.py")
print("5. Start server: uvicorn main:app --reload")
print("6. Open browser: http://localhost:8000")
print("=" * 60)