# 📄 File: scripts/init_db.py

from sqlmodel import SQLModel
from app.database import engine

# 👇 This is important: import all models so they're registered
from app import models

def init_db():  
    SQLModel.metadata.create_all(engine) # <-- recreate tables as per models
    print("✅ Tables created.")

if __name__ == "__main__":
    init_db()


# SQLModel.metadata.drop_all(engine)   # <-- this will drop all tables
# python3 -m scripts.init_db
