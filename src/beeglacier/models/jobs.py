from peewee import *
import ..settings 

db = SqliteDatabase(settings.DB_PATH)

class Job(Model):
    id = CharField()
    archiveid = CharField()
    job_type = CharField()
    created_at = IntegerField()
    done = IntegerField()
    response = TextField()
    error = IntegerField()

    class Meta:
        database = db # This model uses the "people.db" database.
        table_name = 'jobs'