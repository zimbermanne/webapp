# Shop Management & Accounting System - Web Application

A comprehensive web-based shop management and accounting system built with FastAPI and PostgreSQL. This application provides inventory management, sales tracking, purchase management, expense tracking, financial reporting, user management, and backup functionality.

## Features

### Core Functionality
- **User Authentication**: Secure login system with JWT tokens
- **Role-Based Access Control**: Admin, Manager, and Employee roles
- **Inventory Management**: Add, edit, delete, and track inventory items
- **Sales Management**: Record sales with automatic inventory updates
- **Purchase Management**: Track purchases and update inventory
- **Expense Tracking**: Categorize and track business expenses
- **Financial Reports**: Profit & loss statements, financial summaries
- **Activity Logging**: Track all user actions for audit purposes
- **Backup System**: Create and restore data backups
- **Debtor & Creditor Management**: Track money owed to and by the business

### User Roles
- **Admin**: Full access to all features including user management and backups
- **Manager**: Access to reports, activity logs, and all core features except backups
- **Employee**: Access to inventory, sales, purchases, and expenses

## Technology Stack

### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: SQL toolkit and ORM
- **PostgreSQL**: Robust relational database
- **Pydantic**: Data validation using Python type annotations
- **JWT**: Secure authentication using JSON Web Tokens
- **Passlib/Bcrypt**: Secure password hashing

### Frontend
- **HTML5/CSS3**: Modern, responsive design
- **Vanilla JavaScript**: No framework dependencies
- **REST API**: Full CRUD operations via API endpoints

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

### Database Setup

1. **Install PostgreSQL** if not already installed
2. **Create a database** for the application:
   ```sql
   CREATE DATABASE shop_management;
   ```
3. **Create a database user** (optional, if not using default postgres user):
   ```sql
   CREATE USER shop_user WITH PASSWORD 'your_password';
   GRANT ALL PRIVILEGES ON DATABASE shop_management TO shop_user;
   ```

### Application Setup

1. **Navigate to the webapp directory**:
   ```bash
   cd webapp
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv venv
   
   # On Windows:
   venv\Scripts\activate
   
   # On Unix/MacOS:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Copy the `.env.example` file to `.env` and update the values:
   ```bash
   cp .env .env
   ```
   
   Edit `.env` with your configuration:
   ```env
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/shop_management
   SECRET_KEY=your-secret-key-here-change-in-production
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=30
   ```

5. **Generate a secure secret key**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Use the output as your SECRET_KEY in the `.env` file.

## Running the Application

### Development Mode

1. **Start the FastAPI server**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the application**:
   - Frontend: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Alternative API Docs: http://localhost:8000/redoc

### Production Mode

For production deployment, consider using:
- **Gunicorn** with Uvicorn workers:
  ```bash
  gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
  ```
- **Docker** (see Docker setup below)
- **Process manager** like systemd or supervisor

## Default Credentials

The application creates a default admin user on first run:
- **Username**: `admin`
- **Password**: `admin123`

**Important**: Change the default password immediately after first login!

## API Documentation

The application provides interactive API documentation:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Main API Endpoints

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get access token
- `GET /api/auth/me` - Get current user info
- `PUT /api/auth/change-password` - Change password

#### Inventory
- `GET /api/inventory/` - List all inventory items
- `POST /api/inventory/` - Create new inventory item
- `GET /api/inventory/{item_id}` - Get specific item
- `PUT /api/inventory/{item_id}` - Update item
- `DELETE /api/inventory/{item_id}` - Delete item
- `GET /api/inventory/metrics` - Get inventory metrics

#### Sales
- `GET /api/sales/` - List all sales
- `POST /api/sales/` - Create new sale
- `GET /api/sales/stats/summary` - Get sales summary

#### Purchases
- `GET /api/purchases/` - List all purchases
- `POST /api/purchases/` - Create new purchase
- `GET /api/purchases/stats/summary` - Get purchases summary

#### Expenses
- `GET /api/expenses/` - List all expenses
- `POST /api/expenses/` - Create new expense
- `GET /api/expenses/stats/summary` - Get expenses summary

#### Reports
- `GET /api/reports/financial-summary` - Get financial summary
- `GET /api/reports/profit-loss` - Get profit & loss report
- `GET /api/reports/debtors` - Get debtors report
- `GET /api/reports/creditors` - Get creditors report

#### Users (Admin/Manager only)
- `GET /api/users/` - List all users
- `GET /api/users/{username}` - Get specific user
- `PUT /api/users/{username}` - Update user
- `DELETE /api/users/{username}` - Delete user

#### Activity Logs (Admin/Manager only)
- `GET /api/activity/` - List activity logs
- `GET /api/activity/stats` - Get activity statistics

#### Backup (Admin only)
- `POST /api/backup/create` - Create backup
- `GET /api/backup/list` - List available backups
- `POST /api/backup/restore/{filename}` - Restore backup
- `DELETE /api/backup/{filename}` - Delete backup

## Docker Setup

### Dockerfile

Create a `Dockerfile` in the webapp directory:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create necessary directories
RUN mkdir -p backups static

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  webapp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/shop_management
      - SECRET_KEY=your-secret-key-here
    depends_on:
      - db
    volumes:
      - ./backups:/app/backups

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=shop_management
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Running with Docker

```bash
docker-compose up --build
```

## Database Migrations

For production use, consider using Alembic for database migrations:

1. **Initialize Alembic** (one-time):
   ```bash
   alembic init alembic
   ```

2. **Create a migration**:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

3. **Apply migrations**:
   ```bash
   alembic upgrade head
   ```

## Security Considerations

### Production Deployment
1. **Change the SECRET_KEY** in `.env` to a strong, random value
2. **Use HTTPS** in production (SSL/TLS certificates)
3. **Restrict CORS origins** in production
4. **Use strong database passwords**
5. **Implement rate limiting** for API endpoints
6. **Regular security updates** for dependencies
7. **Backup strategy** with off-site storage
8. **Monitor logs** for suspicious activity

### Environment Variables
- Never commit `.env` files to version control
- Use different environments for development, staging, and production
- Rotate secrets periodically

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
sudo service postgresql status

# Test connection
psql -h localhost -U postgres -d shop_management
```

### Port Already in Use
```bash
# Find process using port 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Unix/Mac

# Kill the process or use a different port
uvicorn main:app --port 8001
```

### Permission Issues
Ensure the application has write permissions for:
- `backups/` directory
- Log files
- Database files (if using SQLite)

## Development

### Adding New Features

1. **Create/update database models** in `models.py`
2. **Add Pydantic schemas** in `schemas.py`
3. **Create API endpoints** in appropriate router file
4. **Update frontend** in `static/` directory
5. **Test endpoints** using Swagger UI at `/docs`

### Code Structure
```
webapp/
├── main.py              # Application entry point
├── database.py          # Database configuration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── auth.py              # Authentication utilities
├── activity.py          # Activity logging
├── routers/             # API route handlers
│   ├── __init__.py
│   ├── auth.py
│   ├── inventory.py
│   ├── sales.py
│   ├── purchases.py
│   ├── expenses.py
│   ├── reports.py
│   ├── users.py
│   ├── backup.py
│   └── activity.py
├── static/              # Frontend files
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── backups/             # Backup storage
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables
└── README.md           # This file
```

## Support and Maintenance

### Regular Tasks
- Review and rotate access tokens
- Monitor disk space for backups
- Check database performance
- Review activity logs
- Update dependencies regularly
- Test backup restoration

### Backup Strategy
- Create backups before major updates
- Store backups in multiple locations
- Test restoration process regularly
- Keep backup retention policy

## License

This project is for educational and small business use. Please check the repository or contact the author for licensing details.

## Credits

Developed by Kikundi cha Uwema and contributors.

## Contributing

Contributions are welcome! Please follow these steps:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

For more information or support, please refer to the in-code documentation or contact the project maintainers.