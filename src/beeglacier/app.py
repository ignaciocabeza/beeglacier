"""
Amazon Glacier Backups
"""
import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from .aws import Glacier
import concurrent.futures
from .db import DB
from .components.form import Form

DB_PATH = 'db.sqlite'

class beeglacier(toga.App):

    glacier_instance = None
    vault_table = None
    headers = ['vaultname','numberofarchives','sizeinbytes']
    account_id = None
    access_key = None
    secret_key = None
    region_name = None

    def create_data_vaults_table(self):
        self.glacier_instance = Glacier(self.account_id,
                                        self.access_key,
                                        self.secret_key,
                                        self.region_name)

        #table parameters
        data = []

        #get vaults
        vaults_response = self.glacier_instance.list_vaults()
        print("1st response")
        vaults = vaults_response["VaultList"]
        while vaults:
            
            # insert vault to data
            for vault in vaults:
                new_row = { key.lower():value for (key,value) in vault.items() if key.lower() in self.headers }
                new_row['sizeinbytes'] = round(new_row['sizeinbytes']/1024/1024,2)
                data.append(new_row)

            # obtain the next page of vaults
            if 'Marker' in vaults_response.keys():
                vaults_response = self.glacier_instance.list_vaults(marker=vaults_response['Marker'])
                vaults = vaults_response["VaultList"]
                print("other responses")
            else:
                vaults = []

        return data

    def callback_row_selected(self, table, row):
        self.input_vault.value = row.vaultname

    def create_vaults_table(self, container):
        
        #create table control
        self.vaults_table = toga.Table(self.headers, data=[], style=Pack(height=300,direction=COLUMN), on_select=self.callback_row_selected)
        container.add(self.vaults_table)

    def refresh_vaults(self, widget):
        widget.title = "Loading..."
        data = self.create_data_vaults_table()
        self.vaults_table.data = data
        widget.title = "Refresh"

    def create_vault(self, widget):
        import pdb; pdb.set_trace()
        self.app_box.style.visibility = 'hidden'
        self.app_box.style.update()
        self.app_box.refresh()
        print ("create vault")

    def pre_init(self):
        self.db = DB(DB_PATH)
        self.account = self.db.get_account()
        if not self.account:
            return False
        else:
            self.account_id = self.account[0]
            self.access_key = self.account[1]
            self.secret_key = self.account[2]
            self.region_name = self.account[3]
            

    def callback_create_account(self,button):

        self.account_id = self.account_form.get_field_value('account_id')
        self.access_key = self.account_form.get_field_value('access_key')
        self.secret_key = self.account_form.get_field_value('secret_key')
        self.region_name = self.account_form.get_field_value('region_name')
        self.db.save_account(self.account_id, self.access_key, 
                             self.secret_key, self.region_name)

    def save_credentials_box(self):
        
        fields = [
            {'name': 'account_id', 'label': 'Account ID:', 'value': self.account_id },
            {'name': 'access_key', 'label': 'Access Key:', 'value': self.access_key },
            {'name': 'secret_key', 'label': 'Secret Key:', 'value': self.secret_key },
            {'name': 'region_name', 'label': 'Region Name:', 'value': self.region_name },
        ]
        confirm = {'label': 'Save credentials', 'callback': self.callback_create_account }
        self.account_form = Form(fields=fields, confirm=confirm)

        return self.account_form.getbox()

    def upload_file(self, button):

        full_path = self.input_path.value
        vault_name = self.input_vault.value
        import ntpath
        filename = ntpath.basename(full_path)
        part_size = 4

        self.upload_id = self.glacier_instance.create_multipart_upload(vault_name, filename, part_size)
        print(self.upload_id)

        response = self.glacier_instance.upload(vault_name, full_path, filename, part_size, 4, self.upload_id)
        print (response)

    def startup(self): 

        self.main_window = toga.MainWindow(title="BeeGlacier", size=(640, 600))
        main_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        
        self.pre_init()
    
        # Vaults Option
        self.app_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))

        # -- nav
        nav_box = toga.Box(style=Pack(direction=ROW, flex=1, padding=10))
        refresh_vaults_button = toga.Button('Refresh Vaults', on_press=self.refresh_vaults)
        nav_box.add(refresh_vaults_button)
        create_vault_button = toga.Button('New Vault', on_press=self.create_vault)
        nav_box.add(create_vault_button)
        self.app_box.add(nav_box)

        # -- table
        list_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))
        self.create_vaults_table(list_box)
        self.app_box.add(list_box)

        # -- add file
        add_file_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))
        self.input_vault = toga.TextInput()
        self.input_path = toga.TextInput()
        self.input_path.value = '/Users/ignaciocabeza/Documents/test.zip'
        self.button_upload = toga.Button('Upload', on_press=self.upload_file)
        add_file_box.add(self.input_vault, self.input_path, self.button_upload)

        self.app_box.add(add_file_box)

        # Option Container
        container = toga.OptionContainer(style=Pack(padding=10, direction=COLUMN))
        container.add('Vaults', self.app_box)
        container.add('Configure', self.save_credentials_box())
        main_box.add(container)

        #build and show main
        self.main_window.content = main_box
        self.main_window.show()

        

def main():
    return beeglacier()