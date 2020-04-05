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
    updated_at = TimestampField(null=True)
    done = IntegerField(default=0)
    response = TextField(null=True)
    archiveid = TextField(default='')
    error = IntegerField(default=0)
    description = TextField(null=True)

    class Meta:
        database = db
        table_name = 'jobs'