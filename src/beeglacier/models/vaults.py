from datetime import datetime

from peewee import (
    Model,
    CharField,
    TextField,
    TimestampField,
    BooleanField
)

from . import db, get_timestamp


class Vault(Model):
    account_id = CharField(primary_key=True)
    updated_at = TimestampField(default=get_timestamp)
    response = TextField()
    
    class Meta:
        database = db
        table_name = 'vaults'
