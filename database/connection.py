import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

def create_db_engine():
    """Create and return a SQLAlchemy engine connected to the PostgreSQL database."""
    POSTGRES_USER = os.environ.get("POSTGRES_USER")
    POSTGRES_PASS = os.environ.get("POSTGRES_PASS")
    POSTGRES_DB = os.environ.get("POSTGRES_DB")
    POSTGRES_IP = "176.108.250.9"
    POSTGRES_PORT = "5432"
    
    connection_string = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASS}@{POSTGRES_IP}:{POSTGRES_PORT}/{POSTGRES_DB}"
    engine = create_engine(connection_string)
    return engine

# Create a global engine instance
engine = create_db_engine()