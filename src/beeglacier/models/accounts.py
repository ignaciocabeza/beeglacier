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
    
    @staticmethod
    def getaccount(response_type=dict):

        account = Account.get_or_none()
        if response_type == object:
            return account
        
        if account:
            return {
                'account_id': account.account_id,
                'access_key': account.access_key,
                'secret_key': account.secret_key,
                'region_name': account.region_name
            }
        else:
            return {}
        
    @staticmethod
    def saveaccount(account):
        required_fields = sorted([
            'account_id', 'access_key', 'secret_key', 'region_name'
        ])

        if required_fields != sorted(account):
            raise Exception(f'Required: {required_fields}')
        
        existing = Account.getaccount(object)
        if existing:
            # update
            update = existing.update(**account)
            update.execute()
        else:
            # new
            new = Account(**account)
            new.save()