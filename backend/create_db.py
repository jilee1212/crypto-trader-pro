"""Create database tables script."""

from app.db.database import engine
from app.models.base import BaseModel
from app.models.user import User

def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    BaseModel.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    create_tables()