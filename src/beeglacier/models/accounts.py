from peewee import Model, CharField

from . import db

class Account(Model):
    account_id = CharField(primary_key=True)
    access_key = CharField()
    secret_key = CharField()
    region_name = CharField()

    class Meta:
        database = db
        table_name = 'accounts'

def getaccount():
    account = Account.get_or_none()
    if account:
        return {
            'account_id': account.account_id,
            'access_key': account.access_key,
            'secret_key': account.secret_key,
            'region_name': account.region_name
        }
    else:
        return {}