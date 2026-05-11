# MySQL Database Configuration Guide

This document explains how to change your Flask application's database from the default SQLite to a MySQL database with a username and password.

## 1. Install Required Dependencies

To connect to a MySQL database, SQLAlchemy needs a database driver. `pymysql` is a widely used, pure-Python MySQL driver that works well on all operating systems.

Install it via the command line:

```bash
pip install pymysql
```

*(Note: Don't forget to update your `requirements.txt` with `pip freeze > requirements.txt` after installing).*

## 2. Update Configuration (`config.py`)

Currently, your `config.py` handles the database connection like this:

```python
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'enterprise_portal.db')
```

Because it prioritizes the `DATABASE_URL` environment variable, you have two options to switch to MySQL:

### Option A: Using Environment Variables (Recommended for Production)

You **do not need to change any code** in `config.py`. You simply need to set the `DATABASE_URL` environment variable on your server or in your `.env` file (if you are using `python-dotenv`).

Set the variable to the following format:

```env
DATABASE_URL="mysql+pymysql://<username>:<password>@<host>:<port>/<database_name>"
```

**Example:**
```env
DATABASE_URL="mysql+pymysql://admin:MySecurePass123!@localhost:3306/enterprise_portal_db"
```

### Option B: Hardcoding in `config.py` (For Testing/Local Use Only)

If you prefer to change the code directly in `config.py`, replace the `sqlite:///` fallback string with your MySQL connection string.

**Change this:**
```python
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'enterprise_portal.db')
```

**To this:**
```python
    # Format: mysql+pymysql://username:password@server/db
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://your_username:your_password@localhost:3306/your_database_name'
```

## 3. Database Initialization

After making this change, you will need to create the database in MySQL and run your Flask-Migrate or `db.create_all()` commands to generate the tables, as MySQL will not automatically create the database file like SQLite does.

1. Log into your MySQL server and run:
   ```sql
   CREATE DATABASE your_database_name;
   ```
2. Run your Flask application or database initialization scripts to generate the tables.
