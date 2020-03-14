from datetime import datetime
from peewee import SqliteDatabase

from ..settings import (
    DB_PATH
)

db = SqliteDatabase(DB_PATH)

def get_timestamp():
    return datetime.timestamp(datetime.now())