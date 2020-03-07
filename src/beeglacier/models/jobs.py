from peewee import *

from ..settings import (
    DB_PATH, 
    SQL_TIMESTAMP
) 

db = SqliteDatabase(DB_PATH)

class Job(Model):
    id = CharField()
    archiveid = TextField()
    job_type = CharField()
    created_at = TimestampField(default=SQL_TIMESTAMP)
    done = BooleanField()
    response = TextField()
    error = BooleanField()

    class Meta:
        database = db
        table_name = 'jobs'