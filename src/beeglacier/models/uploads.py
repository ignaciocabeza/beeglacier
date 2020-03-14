from peewee import (
    Model,
    CharField,
    TextField,
    TimestampField
)

from . import db

class Upload(Model):
    upload_id = TextField(primary_key=True)
    account_id = CharField()
    filepath = CharField()
    vault = CharField()
    response = TextField()
    
    class Meta:
        database = db
        table_name = 'uploads'