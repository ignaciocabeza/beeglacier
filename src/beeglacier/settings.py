import os
from pathlib import Path

DB_PATH = os.path.join(Path.home(), '.beeglacier.sqlite')

HEADERS = [
    {'name': 'vaultname', 'label': 'Name'},
    {'name': 'numberofarchives', 'label': '# Archives'},
    {'name': 'sizeinbytes', 'label': 'Size (MB)'},
]

HEADERS_ARCHIVES = [
    {'name': 'archivedescription', 'label': 'Filename'},
    {'name': 'size', 'label': 'Size (MB)'},
]

HEADERS_ON_PROGRESS = [
    {'name': 'description', 'label': 'Task Description'},
    {'name': 'progress', 'label': 'Progress'}
]

HEADERS_DOWNLOADS_JOBS = [
    {'name': 'description', 'label': 'Job Description'},
]

HEADERS_DOWNLOADS_CURRENT = [
    {'name': 'description', 'label': 'Download Description'},
    {'name': 'progress', 'label': 'Progress'}
]

HEADERS_JOBS = [
    {'name': 'description', 'label': 'Job Description'},
    {'name': 'status', 'label': 'Status'}
]
