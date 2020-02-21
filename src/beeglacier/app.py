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
from .utils import ObsData, Controls
from .utils.aws import Glacier

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

TEXT = {
    'PENDING_INVENTORY_JOBS': 'Pending Inventory Jobs: ',
}

global_controls = Controls()

class beeglacier(toga.App):

    glacier_instance = None
    vaults_table = None
    account_id = None
    access_key = None
    secret_key = None
    region_name = None
    # observables datas
    obs_data_vaults = None
    obs_data_archives = None
    obs_selected_vault = None
    obs_selected_archive = None

    def callback_row_selected(self, table, row):
        delete_vault = global_controls.get_control_by_name('Vaults_TopNav_DeleteVault')
        if delete_vault:
            pass

        self.obs_selected_vault.data = row.name

    def callback_row_selected_archive(self, table, row):
        if row:
            print (row.filename)
            self.obs_selected_archive.data = row.filename

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

    def obs_data_table_archives(self, test):
        self.archives_table.set_data(self.obs_data_archives.data)

    def obs_selected_archive_callback(self, test):
        label_selected_arcvhie = global_controls.get_control_by_name('VaultDetail_ArchiveTitle')
        label_selected_arcvhie.text = "Archive Selected: " + self.obs_selected_archive.data

    def obs_selected_vault_callback(self, test):
        # Update selected Vault in 'Vault Detail' Option
        label_selected_vault = global_controls.get_control_by_name('VaultDetail_VaultTitle')
        label_selected_vault.text = "Selected: " + self.obs_selected_vault.data

        # Update Vault Name input in Upload Form
        upload_vault_input = global_controls.get_control_by_name('Vaults_Upload_VaultName')
        upload_vault_input.text = self.obs_selected_vault.data

    def on_btn_request_download_job(self, button):
        response = self.glacier_instance.initiate_archive_retrieval(self.obs_selected_vault.data, self.obs_selected_archive.data)
        self.db.create_job(self.obs_selected_vault.data, response.id, 'archive')

    def on_delete_vault(self, button):

        # check if vault has archvies.
        target_vault = list( filter(lambda x: x['vaultname']==self.obs_selected_vault.data, self.obs_data_vaults.data) )  
        if len(target_vault) and target_vault[0]['numberofarchives'] > 0:
            self.main_window.error_dialog('Error', 'Cannot delete a vault with archives inside')
            return None
        
        # confirmation dialog
        if self.obs_selected_vault.data:
            msg = "Do you want to delete '%s' " % (self.obs_selected_vault.data)
            res = self.main_window.confirm_dialog("Delete Vault", msg)
            if res:
                self.glacier_instance.delete_vault(self.obs_selected_vault.data)
        else:
            self.main_window.error_dialog("Error", "Vault not selected")

    def on_create_vault_dialog(self, button):
        if self.input_vault_name.value:
            self.glacier_instance.create_vault(self.input_vault_name.value)
            self.create_vault_dialog.close()

    def on_create_vault(self, widget):
        self.create_vault_dialog = toga.Window(title='Create New Vault', resizeable=False, size=(300, 120))
        self.input_vault_name = toga.TextInput(style=Pack(padding=3))
        lbl_vaultname = toga.Label("Vault Name",style=Pack(padding=3))        
        btn_create = toga.Button("Create New", on_press=self.on_create_vault_dialog,style=Pack(padding=3))
        box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=15))
        box.add(lbl_vaultname)
        box.add(self.input_vault_name)
        box.add(btn_create)
        self.create_vault_dialog.content = box
        self.create_vault_dialog.show()

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
            self.glacier_instance = Glacier(self.account_id, self.access_key,
                                            self.secret_key, self.region_name)

            
    def callback_create_account(self,button):
        # called after pressed save button
        self.account_id = self.account_form.get_field_value('account_id')
        self.access_key = self.account_form.get_field_value('access_key')
        self.secret_key = self.account_form.get_field_value('secret_key')
        self.region_name = self.account_form.get_field_value('region_name')
        self.db.save_account(self.account_id, self.access_key, 
                             self.secret_key, self.region_name)

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
        input_path = global_controls.get_control_by_name('Vaults_Upload_VaultPath')
        full_path = input_path.value
        vault_name = self.obs_selected_vault.data

        
        if full_path and vault_name:
            x = threading.Thread(target=self.bg_upload_file, args=(vault_name,full_path))
            threads = list()
            threads.append(x)
            x.start()

            #x = threading.Thread(target=self.bg_refresh_upload, args=())
        else:
            if not full_path:
                error_msg = 'File not selected'
            else:
                error_msg = 'Vault not selected'
            self.main_window.error_dialog("Error", error_msg)

    def on_searchfile_btn(self, button):
        filepath = self.main_window.open_file_dialog("Select File to upload")
        input_filepath = global_controls.get_control_by_name('Vaults_Upload_VaultPath')
        if filepath:
            input_filepath.value = filepath

    def on_btn_get_inventory(self, button):
        response = self.glacier_instance.initiate_inventory_retrieval(self.obs_selected_vault.data)
        self.db.create_job(self.obs_selected_vault.data, response.id, 'inventory')

    def on_btn_check_jobs(self, button):
        jobs = self.db.get_inventory_jobs(self.obs_selected_vault.data)
        for job in jobs:
            job_id = job[0]
            job_description = self.glacier_instance.describe_job(self.obs_selected_vault.data, job_id)
            if job_description['Completed'] and job_description['StatusCode'] == 'Succeeded':
                job_result = self.glacier_instance.get_job_output(self.obs_selected_vault.data, job_id)
                if job_result['status'] == 200:
                    job_dict = json.loads(job_result['body'].read().decode())
                    self.db.update_job(job_id, job_dict ,1)
        
        self.select_option_vault_details()

    def on_select_option(self, interface, option):
        # Hack for rewriting UI and autoresizing controls
        option.refresh()

        # Actions triggered after selecting options
        option_1 = getattr(self, 'app_box', None)
        option_2 = getattr(self, 'vault_box', None)
        option_3 = getattr(self, 'credentials_box', None)
        if option == option_2:
            self.select_option_vault_details()

    def select_option_vault_details(self):
        """ Actions after selecting Vault Detail Option
            - Get Pending Jobs
            - Populate Vault Archive Table
        """
        self.obs_data_archives.data = []
        jobs = self.db.get_inventory_jobs(self.obs_selected_vault.data)
        self.vault_pending_jobs.text = '%s %s' % (TEXT['PENDING_INVENTORY_JOBS'],str(len(jobs)))

        done_jobs = self.db.get_inventory_jobs(self.obs_selected_vault.data, status='finished')
        if len(done_jobs):
            last_job_done = json.loads(done_jobs[0][1])
            list_archives = last_job_done['ArchiveList']
            data = []
            for archive in list_archives:
                new_row = { key.lower():value for (key,value) in archive.items() }
                new_row['size'] = round(new_row['size']/1024/1024,2)
                data.append(new_row)

            self.obs_data_archives.data = data

    def create_controls(self):

        # Vaults: Box
        self.app_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))
        global_controls.add('Vaults', self.app_box.id)

        # Vaults -> Top Nav: Box
        self.nav_box = toga.Box(style=Pack(direction=ROW, flex=1, alignment="top"))
        self.app_box.add(self.nav_box)
        global_controls.add('Vaults_TopNav', self.nav_box.id)

        # Vaults -> Top Nav -> RefreshVautls: Button
        self.refresh_vaults_button = toga.Button('Refresh Vaults', on_press=self.on_refresh_vaults)
        self.nav_box.add(self.refresh_vaults_button)
        global_controls.add('Vaults_TopNav_RefreshVaults', self.refresh_vaults_button.id)

        # Vaults -> Top Nav -> CreateVault: Button
        create_vault_button = toga.Button('New Vault', on_press=self.on_create_vault)
        self.nav_box.add(create_vault_button)
        global_controls.add('Vaults_TopNav_NewVault', create_vault_button.id)

        # Vaults -> Top Nav -> DeleteVault: Button
        delete_vault_btn = toga.Button('Delete Vault', enabled=False, on_press=self.on_delete_vault)
        global_controls.add('Vaults_TopNav_DeleteVault', delete_vault_btn.id)
        self.nav_box.add(delete_vault_btn)

        # Vautls -> TableContainer: Box
        list_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding_top=5, alignment="top"))
        self.app_box.add(list_box)
        global_controls.add('Vaults_TableContainer', list_box.id)

        # Vautls -> TableContainer -> VaultsTable: Table
        self.vaults_table = Table(headers=HEADERS, on_row_selected=self.callback_row_selected)
        list_box.add(self.vaults_table.getbox())
        global_controls.add_from_controls(self.vaults_table.getcontrols(),'Vaults_TableContainer_')

        # Vaults -> Upload: Box
        add_file_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding_top=20))
        self.app_box.add(add_file_box)
        global_controls.add('Vaults_Upload', add_file_box.id)

        # Vaults -> Upload -> Title: Box
        upload_vault_title_box = toga.Box(style=Pack(direction=ROW, flex=1))
        add_file_box.add(upload_vault_title_box)
        global_controls.add('Vaults_Upload_Title', upload_vault_title_box.id)

        # Vaults -> Upload -> Title -> Label: Label
        vault_title_label = toga.Label('Upload to Vault:',style=Pack(font_size=16, padding_bottom=5))
        upload_vault_title_box.add(vault_title_label)
        global_controls.add('Vaults_Upload_Title_Label', vault_title_label.id)

        # Vaults -> Upload -> VaultName: TextInput
        label_upload_vaultname = toga.Label('',style=Pack(font_size=16, padding_left=5, width=200))
        upload_vault_title_box.add(label_upload_vaultname)
        global_controls.add('Vaults_Upload_VaultName', label_upload_vaultname.id)

        # Vaults -> Upload -> InputFileBox
        input_file_box = toga.Box(style=Pack(direction=ROW, flex=1, padding_top=5))
        add_file_box.add(input_file_box)
        global_controls.add('Vaults_Upload_InputFileBox', input_file_box.id)

        # Vaults -> Upload -> VaultPath: TextInput
        self.input_path = toga.TextInput(readonly=True, style=Pack(flex=2))
        self.input_path.value = ''
        input_file_box.add(self.input_path)
        global_controls.add('Vaults_Upload_VaultPath', self.input_path.id)
        
        # Vaults -> Upload -> SearchFile: Button
        searchfile_upload = toga.Button('Browse', on_press=self.on_searchfile_btn, 
                                        style=Pack(padding_left=5, flex=1))
        input_file_box.add(searchfile_upload)
        global_controls.add('Vaults_Upload_SearchFileBtn', searchfile_upload.id)

        # Vaults -> Upload -> Button: Button
        self.button_upload = toga.Button('Upload', on_press=self.on_upload_file, 
                                         style=Pack(padding_top=10, width=100,alignment='right'))
        add_file_box.add(self.button_upload)
        global_controls.add('Vaults_Upload_Button', self.button_upload.id)

        # VaultDetail: Box
        self.vault_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding=10))
        global_controls.add('VaultDetail', self.vault_box.id)

        # VaultDetail -> VaultTitle: Label
        self.vault_title = toga.Label('Vault selected: -', style=Pack(font_size=16, padding_bottom=5))
        self.vault_box.add(self.vault_title)
        global_controls.add('VaultDetail_VaultTitle', self.vault_title.id)

        # VaultDetail -> VaultPendingJobs: Label
        self.vault_pending_jobs = toga.Label('%s 0' % (TEXT['PENDING_INVENTORY_JOBS']))
        self.vault_box.add(self.vault_pending_jobs)
        global_controls.add('VaultDetail_VaultPendingJobs', self.vault_pending_jobs.id)

        # VaultDetail -> ArchivesTable: Table
        self.archives_table = Table(headers=HEADERS_ARCHIVES, on_row_selected=self.callback_row_selected_archive)
        self.vault_box.add(self.archives_table.getbox())
        global_controls.add_from_controls(self.archives_table.getcontrols(),'VaultDetail_TableContainer_')

        # VaultDetail -> BottomNav: Box
        self.bottom_nav_vault = toga.Box(style=Pack(direction=ROW, flex=1, padding_top=5))
        self.vault_box.add(self.bottom_nav_vault)
        global_controls.add('Vaults_BottomNavVault', self.bottom_nav_vault.id)

        # VaultDetail -> StartInventoryJobButton: Button
        self.btn_get_inventory = toga.Button('Start Inventory Retrieval Job', on_press=self.on_btn_get_inventory)
        self.bottom_nav_vault.add(self.btn_get_inventory)
        global_controls.add('VaultDetail_StartInventoryJobButton', self.btn_get_inventory.id)

        # VaultDetail -> CheckJobsButton: Button
        self.btn_check_jobs = toga.Button('Check Jobs', on_press=self.on_btn_check_jobs)
        self.bottom_nav_vault.add(self.btn_check_jobs)
        global_controls.add('VaultDetail_CheckJobsButton', self.btn_check_jobs.id)

        # VaultDetail -> ArchiveBox: Box
        self.archive_selected_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding_top=15))
        self.vault_box.add(self.archive_selected_box)
        global_controls.add('Vaults_ArchiveBox', self.archive_selected_box.id)

        # VaultDetail -> VaultTitle: Label
        self.archive_title = toga.Label('Archive selected: -', style=Pack(font_size=16, padding_bottom=5))
        self.archive_selected_box.add(self.archive_title)
        global_controls.add('VaultDetail_ArchiveTitle', self.archive_title.id)

        # VaultDetail -> StartDownloadArchiveJobButton: Button
        self.btn_request_download_job = toga.Button('Start Download Archive Job', on_press=self.on_btn_request_download_job)
        self.archive_selected_box.add(self.btn_request_download_job)
        global_controls.add('VaultDetail_StartDownloadArchiveJobButton', self.btn_request_download_job.id)

        # credentials
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
        account_form = Form(fields=fields, confirm=confirm)
        self.credentials_box = account_form.getbox()
        global_controls.add_from_controls(account_form.getcontrols(),'Credentials_')

        # Main -> OptionContainer: OptionContainer
        container = toga.OptionContainer(style=Pack(padding=10, direction=COLUMN), on_select=self.on_select_option)
        container.add('Vaults', self.app_box)
        container.add('Vault Detail', self.vault_box)
        container.add('Credentials', self.credentials_box)
        self.main_box.add(container)
        global_controls.add('Main_OptionContainer', container.id)

    def startup(self): 
        # setup
        self.pre_init()

        # Main: MainWindow
        self.main_window = toga.MainWindow(title="BeeGlacier", size=(800, 525))
        global_controls.set_window(self.main_window)

        # Main: Box
        self.main_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        global_controls.add('Main', self.main_box.id)

        # Create all controls
        self.create_controls()

        # Show Main Window
        self.main_window.content = self.main_box
        self.main_window.show()

        # ---
        # create observable for storing list of vaults
        self.obs_data_vaults = ObsData()
        self.obs_data_vaults.bind_to(self.obs_data_table)

        self.obs_data_archives = ObsData()
        self.obs_data_archives.bind_to(self.obs_data_table_archives)

        self.obs_selected_vault = ObsData(None)
        self.obs_selected_vault.bind_to(self.obs_selected_vault_callback)

        self.obs_selected_archive = ObsData(None)
        self.obs_selected_archive.bind_to(self.obs_selected_archive_callback)

        # get last retrieve of vaults from database 
        vaults_db = self.db.get_vaults(self.account_id)
        if vaults_db:
            self.obs_data_vaults.data = json.loads(vaults_db)


def main():
    return beeglacier()