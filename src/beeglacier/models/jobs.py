from peewee import (
    Model,
    CharField,
    TextField,
    TimestampField,
    BooleanField,
    IntegerField
)

from . import db, get_timestamp


class Job(Model):
    id = CharField()
    job_id = CharField()
    job_type = CharField()
    created_at = TimestampField(default=get_timestamp)
    updated_at = TimestampField()
    done = IntegerField(default=0)
    response = TextField()
    archiveid = TextField(default='')
    error = IntegerField(default=0)

    class Meta:
        database = db
        table_name = 'jobs'