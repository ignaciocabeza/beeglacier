"""
Amazon Glacier Backups
"""

#Icons made by <a href="https://www.flaticon.com/authors/freepik" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon"> www.flaticon.com</a>

import os
from pathlib import Path
import threading
import ntpath
import json

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import concurrent.futures

from .db import DB
from .components.form import Form
from .components.table import Table
from .utils import ObsData
from .utils.aws import Glacier

DB_PATH = os.path.join(Path.home(), '.beeglacier.sqlite')
HEADERS = [
    {'name': 'vaultname', 'label': 'Name'},
    {'name': 'numberofarchives', 'label': '# Archives'},
    {'name': 'sizeinbytes', 'label': 'Size (MB)'},
]
HEADERS_ARCHIVES = [
    {'name': 'filename', 'label': 'Filename'},
    {'name': 'sizeinbytes', 'label': 'Size (MB)'},
]

class beeglacier(toga.App):

    glacier_instance = None
    vault_table = None
    
    account_id = None
    access_key = None
    secret_key = None
    region_name = None

    # observables datas
    obs_data_vaults = None
    obs_selected_vault = None

    def callback_row_selected(self, table, row):
        self.obs_selected_vault.data = row.name
        self.input_vault.value = row.name

    def bg_get_vaults_data(self):

        # get account info
        db = DB(DB_PATH)
        account_id, access_key, secret_key, region_name = db.get_account()
        
        # create glacier instance
        glacier_instance = Glacier(account_id,
                                access_key,
                                secret_key,
                                region_name)

        # retrieve all vaults of that account
        data = []
        vaults_response = glacier_instance.list_vaults()
        vaults = vaults_response["VaultList"]
        while vaults:
            # insert vault to data
            for vault in vaults:
                new_row = { key.lower():value for (key,value) in vault.items() }
                new_row['sizeinbytes'] = round(new_row['sizeinbytes']/1024/1024,2)
                data.append(new_row)

            # obtain the next page of vaults
            if 'Marker' in vaults_response.keys():
                vaults_response = glacier_instance.list_vaults(marker=vaults_response['Marker'])
                vaults = vaults_response["VaultList"]
            else:
                vaults = []

        # save to database
        db.create_vaults(account_id, json.dumps(data))

        # update observer
        self.obs_data_vaults.data = data

        # refresh UI
        self.refresh_vaults_button.label = "Refresh Vaults"
        self.refresh_vaults_button.refresh()

    def bg_upload_file(self, vault, path):

        db = DB(DB_PATH)
        account_id, access_key, secret_key, region_name = db.get_account()

        filename = ntpath.basename(path)
        part_size = 4

        upload_id = self.glacier_instance.create_multipart_upload(vault, filename, part_size)
        db.create_upload(self.account_id, upload_id, path, vault)

        response = self.glacier_instance.upload(vault, path, filename, part_size, 4, upload_id)
        db.save_upload_response(upload_id, json.dumps(response))

    def obs_data_table(self, test):
        # observable function from data_vaults object
        self.vaults_table.set_data(self.obs_data_vaults.data)

    def obs_selected_vault_callback(self, test):
        self.vault_title.text = "Selected: " + self.obs_selected_vault.data

    def create_vault(self, widget):
        print ("Not implemented")

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
            self.glacier_instance = Glacier(self.account_id,
                                            self.access_key,
                                            self.secret_key,
                                            self.region_name)

            
    def callback_create_account(self,button):
        # called after pressed save button
        self.account_id = self.account_form.get_field_value('account_id')
        self.access_key = self.account_form.get_field_value('access_key')
        self.secret_key = self.account_form.get_field_value('secret_key')
        self.region_name = self.account_form.get_field_value('region_name')
        self.db.save_account(self.account_id, self.access_key, 
                             self.secret_key, self.region_name)

    def save_credentials_box(self):
        fields = [
            {
                'name': 'account_id', 
                'label': 'Account ID:', 
                'value': self.account_id, 
                'validate': ['notnull'],
            },
            {
                'name': 'access_key', 
                'label': 'Access Key:', 
                'value': self.access_key 
            },
            {
                'name': 'secret_key', 
                'label': 'Secret Key:', 
                'value': self.secret_key 
            },
            {
                'name': 'region_name', 
                'label': 'Region Name:', 
                'value': self.region_name 
            },
        ]
        confirm = {
            'label': 'Save credentials', 
            'callback': self.callback_create_account 
        }
        self.account_form = Form(fields=fields, confirm=confirm)
        return self.account_form.getbox()

    def on_refresh_vaults(self, button, **kwargs):
        # callback for button
        self.refresh_vaults_button.label = "Loading...     "
        self.refresh_vaults_button.refresh()

        # fetch data with a thread
        x = threading.Thread(target=self.bg_get_vaults_data, args=())
        threads = list()
        threads.append(x)
        x.start()

    def on_upload_file(self, button):
        
        full_path = self.input_path.value
        vault_name = self.input_vault.value

        x = threading.Thread(target=self.bg_upload_file, args=(vault_name,full_path))
        threads = list()
        threads.append(x)
        x.start()

    def on_btn_get_inventory(self, button):
        response = self.glacier_instance.initiate_inventory_retrieval(self.obs_selected_vault.data)
        self.db.create_job(self.obs_selected_vault.data, response.id, 'inventory')

    def on_select_option(self,interface, option):
        option.refresh()
        '''
        if option == self.credentials_box:
            reduce_to = 350
            self.main_window.size = (self.main_window.size[0], reduce_to)
        else:
            self.main_window.size = (self.main_window.size[0], 480)    
        '''

    def startup(self): 
        # setup
        self.pre_init()

        # create observable for storing list of vaults
        self.obs_data_vaults = ObsData()
        self.obs_data_vaults.bind_to(self.obs_data_table)

        self.obs_selected_vault = ObsData(None)
        self.obs_selected_vault.bind_to(self.obs_selected_vault_callback)

        # create main window
        self.main_window = toga.MainWindow(title="BeeGlacier", size=(640, 600))
        main_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
    
        # Vaults Option
        self.app_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))

        # -- nav
        self.nav_box = toga.Box(style=Pack(direction=ROW, flex=1, padding=10))
        self.refresh_vaults_button = toga.Button('Refresh Vaults', on_press=self.on_refresh_vaults)
        self.nav_box.add(self.refresh_vaults_button)
        create_vault_button = toga.Button('New Vault', on_press=self.create_vault)
        self.nav_box.add(create_vault_button)
        self.app_box.add(self.nav_box)

        # -- table
        list_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))
        self.vaults_table = Table(headers=HEADERS, on_row_selected=self.callback_row_selected)
        list_box.add(self.vaults_table.getbox())
        self.app_box.add(list_box)

        # -- add file
        add_file_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))
        self.input_vault = toga.TextInput()
        self.input_path = toga.TextInput()
        self.input_path.value = '/Users/ignaciocabeza/Documents/test.zip'
        self.button_upload = toga.Button('Upload', on_press=self.on_upload_file)
        add_file_box.add(self.input_vault, self.input_path, self.button_upload)
        self.app_box.add(add_file_box)

        # Vaults info
        self.vault_title = toga.Label('Selected: ')
        self.btn_get_inventory = toga.Button('Start Inventory Retrieval Job', on_press=self.on_btn_get_inventory)
        self.vault_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))
        self.archives_table = Table(headers=HEADERS_ARCHIVES, on_row_selected=self.callback_row_selected)
        
        self.vault_box.add( self.vault_title, self.btn_get_inventory, self.archives_table.getbox())

        # Option Container
        container = toga.OptionContainer(style=Pack(padding=10, direction=COLUMN), on_select=self.on_select_option)
        container.add('Vaults', self.app_box)
        container.add('Vault Info', self.vault_box)
        self.credentials_box = self.save_credentials_box()
        container.add('Configure', self.credentials_box)
        main_box.add(container)

        # get last retrieve of vaults from database 
        vaults_db = self.db.get_vaults(self.account_id)
        if vaults_db:
            self.obs_data_vaults.data = json.loads(vaults_db)

        #build and show main
        self.main_window.content = main_box
        self.main_window.show()

def main():
    return beeglacier()