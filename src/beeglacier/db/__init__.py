"""import sqlite3
import json

class DB:
    
    def __init__(self, database):
        self.conn = sqlite3.connect(database)
        self._create_if_not_exists()

    def _create_if_not_exists(self):
        #account table
        check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='accounts';"
        c = self.conn.cursor()
        c.execute(check_sql)
        if not c.fetchone():
            create_sql = "CREATE TABLE accounts (account_id, access_key, secret_key, region_name);"
            c.execute(create_sql)
            self.conn.commit()

        #uploads table
        check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='uploads';"
        c = self.conn.cursor()
        c.execute(check_sql)
        if not c.fetchone():
            create_sql = "CREATE TABLE uploads (account_id, upload_id, filepath, vault, response);"
            c.execute(create_sql)
            self.conn.commit()

        #vautls table
        check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='vaults';"
        c = self.conn.cursor()
        c.execute(check_sql)
        if not c.fetchone():
            create_sql = "CREATE TABLE vaults (account_id, response, updated_at INTEGER);"
            c.execute(create_sql)
            self.conn.commit()

        #jobs table
        check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';"
        c = self.conn.cursor()
        c.execute(check_sql)
        if not c.fetchone():
            create_sql = "CREATE TABLE jobs (id, archiveid, job_id, job_type, created_at INTEGER, updated_at INTEGER, done INTEGER, response, error INTEGER);"
            c.execute(create_sql)
            self.conn.commit()
        
        #deleted archives table
        check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='deleted_archives';"
        c = self.conn.cursor()
        c.execute(check_sql)
        if not c.fetchone():
            create_sql = "CREATE TABLE deleted_archives (vaultname, archiveid, response, deleted_at INTEGER);"
            c.execute(create_sql)
            self.conn.commit()

    def create_upload(self, account_id, upload_id, filepath, vault):
        sql = "INSERT INTO uploads (account_id, upload_id, filepath, vault) " + \
              "VALUES ('%s','%s', '%s', '%s');" % (account_id, upload_id, filepath, vault)
        c = self.conn.cursor()
        c.execute(sql)
        self.conn.commit() 

    def save_upload_response(self, upload_id, response):
        sql = "UPDATE uploads SET response='%s' " + \
              "WHERE upload_id = '%s';"
        sql = sql % (response, upload_id)
        c = self.conn.cursor()
        c.execute(sql)
        self.conn.commit() 
"""
"""
def create_job(self, id, job_id, job_type, archive_id=''):
    sql = "INSERT INTO jobs (id, job_id, created_at, job_type, done, error, archiveid) " + \
            "VALUES ('%s','%s', CAST(strftime('%%s','now') as INTEGER), '%s', 0, 0, '%s');" % (id, job_id, job_type, archive_id)
    c = self.conn.cursor()
    c.execute(sql)
    self.conn.commit() 
"""

"""
def get_inventory_jobs(self, vault_name, status = 'pending'):
    done = ' AND done=0 '
    order = 'created_at'
    if status == 'all':
        done = ' '
    elif status == 'pending':
        done = ' AND done=0 '
    elif status == 'finished':
        done = ' AND done=1 AND error=0'
        order = 'updated_at'
    elif status == 'failed':
        done = ' AND done=1 AND error=1'
        order = 'updated_at'
    
    select_sql = "SELECT job_id, response, created_at, updated_at FROM jobs WHERE id='%s' %s ORDER BY %s DESC;" % (vault_name, done, order)
    c = self.conn.cursor()
    c.execute(select_sql)
    jobs = c.fetchall()
    return jobs
"""
"""
def get_archive_jobs(self, archiveid, status = 'pending'):
    done = ' AND done=0 '
    order = 'created_at'
    if status == 'all':
        done = ' '
    if status == 'finished':
        done = ' AND done=1 '
        order = 'updated_at'
        
    select_sql = "SELECT job_id, response, created_at, updated_at FROM jobs WHERE archiveid='%s' %s ORDER BY %s DESC;" % (archiveid, done, order)
    c = self.conn.cursor()
    c.execute(select_sql)
    jobs = c.fetchall()
    return jobs
"""
"""
def update_job(self, job_id, response, status, error=0):
    sql = "UPDATE jobs SET response='%s', done=%s, error=%s updated_at=CAST(strftime('%%s','now') as INTEGER) " + \
            "WHERE job_id = '%s';"
    sql = sql % (json.dumps(response), str(status), error, job_id)
    c = self.conn.cursor()
    c.execute(sql)
    self.conn.commit() 
"""
"""
def create_vaults(self, account_id, response):
    sql = "INSERT INTO vaults (account_id, response, updated_at) " + \
            "VALUES ('%s','%s', CAST(strftime('%%s','now') as INTEGER) );" % (account_id, response)
    c = self.conn.cursor()
    c.execute(sql)
    self.conn.commit()
"""

"""
def get_vaults(self, account_id):
    select_sql = "SELECT response FROM vaults WHERE account_id='%s' ORDER BY updated_at DESC LIMIT 1;" % (account_id)
    c = self.conn.cursor()
    c.execute(select_sql)
    vaults = c.fetchone()
    if vaults:
        return vaults[0]
    else:
        return None
"""
"""
def insert_deleted_archive(self, vaultname, archiveid, response):
    sql = f"INSERT INTO deleted_archives " \
            f"(vaultname, archiveid, response, deleted_at) " \
            f"VALUES ('{vaultname}', '{archiveid}', '{response}', " \
            f"CAST(strftime('%s','now') as INTEGER));"

    cursor = self.conn.cursor()
    cursor.execute(sql)
    self.conn.commit()
"""
