"""
SQLAlchemy declarative base and metadata.
All models must import from this module so Alembic auto-detects tables.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
