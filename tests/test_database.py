from sqlalchemy import text
from src.database.connection import engine


def test_mysql_connection():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar()

    assert result == 1


def test_correct_database_selected():
    with engine.connect() as connection:
        database_name = connection.execute(
            text("SELECT DATABASE()")
        ).scalar()

    assert database_name == "wastewise_ai"
