from peewee import (
    Model,
    CharField,
    TextField,
    TimestampField,
    BooleanField
)

from . import db
from ..settings import (
    SQL_TIMESTAMP
)


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