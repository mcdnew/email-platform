# migrations/env.py

import os
import sys
import sqlmodel               # ← ensure migrations can reference `sqlmodel`
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel

# load your .env and app settings
from dotenv import load_dotenv
load_dotenv()
from app.config import settings
from app.models import Prospect, EmailTemplate, Sequence, SequenceStep, ScheduledEmail, SentEmail

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# override the sqlalchemy.url in alembic.ini with your env var, if present
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# ---- HERE WE HOOK IN OUR METADATA ----
target_metadata = SQLModel.metadata


def run_migrations_offline():
    """
    Run migrations in 'offline' mode.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Run migrations in 'online' mode.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # include here any process_revision_directives hooks if you need them
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

