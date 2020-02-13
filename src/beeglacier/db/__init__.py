import sqlite3

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

        #jobs table
        check_sql = "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs';"
        c = self.conn.cursor()
        c.execute(check_sql)
        if not c.fetchone():
            create_sql = "CREATE TABLE jobs (account_id, job_id, type, created_at, updated_at, done, response);"
            c.execute(create_sql)
            self.conn.commit()

    def get_account(self):
        select_sql = "SELECT * FROM accounts"
        c = self.conn.cursor()
        c.execute(select_sql)
        account = c.fetchone()
        return account

    def save_account(self, account_id, access_key, secret_key, region_name):
        existing_account = self.get_account()
        if existing_account:
            existing_account_id = existing_account[0]
            sql = "UPDATE accounts SET account_id='%s', access_key='%s', secret_key='%s', region_name='%s' " + \
                  "WHERE account_id='%s';" 
            sql = sql % (account_id,access_key, secret_key, region_name, existing_account_id)
        else:
            sql = "INSERT INTO accounts (account_id, access_key, secret_key, region_name) " + \
                  "VALUES ('%s','%s', '%s', '%s');" % (account_id,access_key, secret_key, region_name)
        
        c = self.conn.cursor()
        c.execute(sql)
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

    def create_job(self, account_id, job_id, job_type):
        sql = "INSERT INTO uploads (accoun_id, job_id, job_type, done) " + \
              "VALUES ('%s','%s', '%s', 0);" % (account_id, job_id, job_type)
        c = self.conn.cursor()
        c.execute(sql)
        self.conn.commit() 
