from . import db
from .accounts import Account
from .deleted_archives import DeletedArchive
from .jobs import Job
from .uploads import Upload
from .vaults import Vault

def create_tables():
    with db:
        db.create_tables([Account, DeletedArchive, Job, Upload, Vault])