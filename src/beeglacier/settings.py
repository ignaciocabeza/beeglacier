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
    {'name': 'deletion_in_progress', 'label': 'Deleting?'},
]

HEADERS_ON_PROGRESS = [
    {'name': 'description', 'label': 'Task Description'},
    {'name': 'status', 'label': 'Status'},
    {'name': 'progress', 'label': 'Progress'}
]

HEADERS_DOWNLOADS_JOBS = [
    {'name': 'description', 'label': 'Job Description'},
    {'name': 'vaultname', 'label': 'Vault'},
]

HEADERS_DOWNLOADS_CURRENT = [
    {'name': 'vaultname', 'label': 'Vault'},
    {'name': 'description', 'label': 'Download Description'},
    {'name': 'status', 'label': 'Status'},
    {'name': 'progress', 'label': 'Progress'}
]

HEADERS_JOBS = [
    {'name': 'description', 'label': 'Job Description'},
    {'name': 'status', 'label': 'Status'}
]

# Possible status of uploads
STATUS_CHOICES = [
    (0, 'Uploading'),
    (1, 'Stopped'),
    (2, 'Aborted'),
    (3, 'Completed'),
    (4, 'Error')
]

UPLOAD_PART_SIZE = 10
DOWNLOAD_PART_SIZE = 10