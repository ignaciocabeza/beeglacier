import os
from pathlib import Path

DB_PATH = os.path.join(Path.home(), '.beeglacier.sqlite')

SQL_TIMESTAMP = "CAST(strftime('%s','now') as INTEGER))"