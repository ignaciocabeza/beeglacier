from peewee import SqliteDatabase

from ..settings import (
    DB_PATH
)

db = SqliteDatabase(DB_PATH)