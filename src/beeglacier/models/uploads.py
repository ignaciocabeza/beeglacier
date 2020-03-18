from peewee import (
    Model,
    CharField,
    TextField,
    TimestampField,
    IntegerField
)

from . import db
from ..settings import STATUS_CHOICES

class Upload(Model):
    upload_id = TextField(primary_key=True)
    account_id = CharField()
    filepath = CharField()
    vault = CharField()
    response = TextField()
    status = IntegerField(default=0, choices=STATUS_CHOICES)
    parts = IntegerField(default=0)
    parts_done = IntegerField(default=0)
    
    class Meta:
        database = db
        table_name = 'uploads'