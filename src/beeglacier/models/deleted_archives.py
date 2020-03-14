from peewee import (
    Model,
    CharField,
    TextField,
    TimestampField
)

from . import db, get_timestamp
from ..settings import (
    SQL_TIMESTAMP
)


class DeletedArchive(Model):
    vaultname = CharField()
    archiveid = TextField()
    response = TextField()
    deleted_at = TimestampField(default=get_timestamp)
    
    class Meta:
        database = db
        table_name = 'deleted_archives'