
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

# Find the main project folder
PROJECT_DIR = Path(__file__).resolve().parents[2]

# Load database settings from .env
load_dotenv(PROJECT_DIR / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Check required settings
if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError("Database settings missing. Check your .env file.")

# Create MySQL connection
database_url = URL.create(
    drivername="mysql+pymysql",
    username=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=int(DB_PORT),
    database=DB_NAME
)

engine = create_engine(database_url, pool_pre_ping=True)


def test_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT DATABASE()"))

        print("MySQL connection successful!")
        print("Connected database:", result.scalar())


if __name__ == "__main__":
    test_connection()
