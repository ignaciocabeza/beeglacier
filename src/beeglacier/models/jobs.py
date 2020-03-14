from peewee import (
    Model,
    CharField,
    TextField,
    TimestampField,
    BooleanField,
    IntegerField
)

from . import db, get_timestamp
from ..settings import (
    SQL_TIMESTAMP
)


class Job(Model):
    id = CharField()
    job_id = CharField()
    archiveid = TextField(default='')
    job_type = CharField()
    response = TextField()
    created_at = TimestampField(default=get_timestamp)
    done = IntegerField(default=0)
    error = IntegerField(default=0)

    class Meta:
        database = db
        table_name = 'jobs'