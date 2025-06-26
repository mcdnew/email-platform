# 📄 File: scripts/init_db.py

from sqlmodel import SQLModel
from app.database import engine

# 👇 This is important: import all models so they're registered
from app import models

def init_db():
    SQLModel.metadata.create_all(engine)
    print("✅ Tables created.")

if __name__ == "__main__":
    init_db()

