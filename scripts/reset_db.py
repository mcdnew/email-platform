# scripts/reset_db.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.models import SQLModel
from app.database import engine

SQLModel.metadata.drop_all(engine)
SQLModel.metadata.create_all(engine)

print("✅ Database reset successfully.")

