"""
Amazon Glacier Backups
"""

#Icons made by <a href="https://www.flaticon.com/authors/freepik" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon"> www.flaticon.com</a>

import os
from pathlib import Path
import threading
import ntpath
import json
import tempfile
import time

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
import concurrent.futures

from .db import DB
from .components.form import Form
from .components.table import Table
from .utils import ObsData, Controls
from .utils.aws import Glacier
from .utils.strings import TEXT
from .utils.styles import STYLES

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
    {'name': 'progress', 'label': 'Progress'},
]

global_controls = Controls()

class beeglacier(toga.App):

    glacier_instance = None
    vaults_table = None
    account_id = None
    access_key = None
    secret_key = None
    region_name = None

    bgtasks = list()

    # observables datas
    obs_data_archives = None
    obs_selected_vault = None
    obs_selected_archive = None

    def _connect_db_and_glacier(self):
        db = DB(DB_PATH)
        aid, akey, skey, reg = db.get_account()
        if not self.glacier_instance:
            self.glacier_instance = Glacier(aid, akey, skey, reg)
        return db, self.glacier_instance

    def _update_control_label(self, name, value):
        """ Given a name, update label text.
        """
        control = global_controls.get_control_by_name(name)
        if type(control) == toga.Label:
            control.text = value
        if type(control) == toga.Button:
            control.label = value
        
        # forcing resizing 
        control.refresh()

    def _execute_bg_task(self, task, *args, **kwargs):
        """ Execute a task in background to avoid freezing UI
        """
        x = threading.Thread(target=task, args=args, kwargs=kwargs)
        self.bgtasks.append(x)
        x.start()

    def callback_row_selected(self, row):
        """ Callback when vault row is selected
        """
        # Update Labels
        selected_vault_text = TEXT['LABEL_SELECTED_VAULT'] % (row['vaultname'])
        self._update_control_label('VaultDetail_VaultTitle', selected_vault_text)
        upload_vault_text = TEXT['LABEL_UPLOAD_VAULT'] % (row['vaultname'])
        self._update_control_label('Vaults_Upload_VaultName', upload_vault_text)
        delete_vault_text = TEXT['BTN_DELETE_VAULT'] % (row['vaultname'])
        self._update_control_label('Vaults_TopNav_DeleteVault', delete_vault_text)

    def bg_get_vaults_data(self):
        # get account info and create glacier instance
        # In background task is necessary to do this
        db, glacier = self._connect_db_and_glacier()

        onprogressid = self.progress_table.append({'description': 'Get Vaults', 'progress': 'on progress'})
        self._update_control_label('Vaults_TopNav_RefreshVaults', 
                                   TEXT['BTN_REFRESH_VAULTS_LOADING'])

        # retrieve all vaults of that account
        data = []
        vaults_response = glacier.list_vaults()
        vaults = vaults_response["VaultList"]
        while vaults:
            # insert vault to data
            for vault in vaults:
                new_row = { key.lower():value for (key,value) in vault.items() }
                new_row['sizeinbytes'] = round(new_row['sizeinbytes']/1024/1024,2)
                data.append(new_row)

            # obtain the next page of vaults
            if 'Marker' in vaults_response.keys():
                vaults_response = glacier.list_vaults(marker=vaults_response['Marker'])
                vaults = vaults_response["VaultList"]
            else:
                vaults = []

        # save to database
        db.create_vaults(glacier.account_id, json.dumps(data))

        # update table
        self.vaults_table.data = data

        # refresh UI
        self._update_control_label('Vaults_TopNav_RefreshVaults', 
                                   TEXT['BTN_REFRESH_VAULTS'])
    
    def bg_tasks_checker(self):
        db, glacier = self._connect_db_and_glacier()
        while True:
            data = []
            if glacier.current_uploads:
                for key, v in glacier.current_uploads.items():
                    progress = f'{v["done"]}/{v["total_parts"]}'
                    description = f'Uploading: {v["description"]}'
                    data.append({'description': description, 'progress': progress})
            
            self.progress_table.data = data
            self.progress_table.refresh()
            time.sleep(2)

    def bg_upload_file(self, *args, **kwargs):
        """ Background task for uploading files
        """

        if 'vaultname' not in kwargs or 'fullpath' not in kwargs:
            return

        vault = kwargs['vaultname']
        path = kwargs['fullpath']

        db, glacier = self._connect_db_and_glacier()
        db = DB(DB_PATH)

        filename = ntpath.basename(path)
        partsize = 4

        upload_id = glacier.create_multipart_upload(vault, filename, partsize)
        db.create_upload(glacier.account_id, upload_id, path, vault)

        response = glacier.upload(vault, path, filename, partsize, 4, upload_id)
        db.save_upload_response(upload_id, json.dumps(response))

    def bg_delete_vault(self, *args, **kwargs):
        db, glacier = self._connect_db_and_glacier()
        
        if 'vaultname' in kwargs:
            vaultname = kwargs['vaultname']
            # Update text
            delete_vault_loading = TEXT['BTN_DELETE_VAULT_LOADING'] % (vaultname)
            self._update_control_label('Vaults_TopNav_DeleteVault', delete_vault_loading)
            # delete
            glacier.delete_vault(vaultname)
            # Update text
            delete_vault_text = TEXT['BTN_DELETE_VAULT'] % (vaultname)
            self._update_control_label('Vaults_TopNav_DeleteVault', delete_vault_text)
            # refresh
            self.bg_get_vaults_data()

    def callback_row_selected_archive(self, table, row):
        if row:
            print (row.filename)
            self.obs_selected_archive.data = row.filename

    def obs_data_table_archives(self, test):
        self.archives_table.data = self.obs_data_archives.data

    def get_archive_from_data(self, archivename):
        target_archive = list( filter(lambda x: x['archivedescription']==self.obs_selected_archive.data, self.obs_data_archives.data) )
        if target_archive:
            return target_archive[0]
        else:
            return None

    def obs_selected_archive_callback(self, test):
        label_selected_archive = global_controls.get_control_by_name('VaultDetail_ArchiveTitle')
        label_selected_archive.text = "Archive Selected: " + self.obs_selected_archive.data

        archive = self.get_archive_from_data(self.obs_selected_archive.data)
        if archive:
            jobs = self.db.get_archive_jobs(archive['archiveid'])
            count_jobs = len(jobs)
            label_pending_downloads = global_controls.get_control_by_name('VaultDetail_PendingDownload')
            label_pending_downloads.text = '%s %s' % (TEXT['PENDING_ARCHIVE_JOBS'],str(count_jobs))

    def on_btn_download_archive(self, button):
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glacier.html#Glacier.Client.get_job_output
        archive = self.get_archive_from_data(self.obs_selected_archive.data)
        file_path_temp = '/users/ignaciocabeza/downloads/' + self.obs_selected_archive.data + '.downloading'
        file_path_final = file_path = '/users/ignaciocabeza/downloads/' + self.obs_selected_archive.data

        if archive:
            jobs = self.db.get_archive_jobs(archive['archiveid'])
            if jobs:
                job_id = jobs[0][0]
                
                job_description = self.glacier_instance.describe_job(self.obs_selected_vault.data, job_id)
                print (job_description)
                if job_description['Completed'] and job_description['StatusCode'] == 'Succeeded':
                    archive_checksum = job_description['ArchiveSHA256TreeHash']
                    
                    # size of the file
                    size = job_description['ArchiveSizeInBytes']
                    #print (size)
                    # 4mb parts
                    part_size = 1024 * 1024 * 1

                    # amount of parts
                    parts = int(size) // part_size + 1

                    # requests parts
                    for part_index in range(parts):
                        start_range= part_size * part_index

                        if size - part_size * part_index  < part_size:
                            #last part
                            end_range = size - 1
                        else:
                            end_range = part_size * part_index + part_size - 1
                        
                        param_range = 'bytes=%s-%s' %(str(start_range),str(end_range))
                        #print(param_range)
                        job_result = self.glacier_instance.get_job_output(self.obs_selected_vault.data, job_id, range=param_range)
                        #print (job_result)
                        if job_result['status'] == 206:
                            body = job_result['body'].read()
                            response_checksum = job_result['checksum']
                            #print(response_checksum)

                            fpart = tempfile.TemporaryFile()
                            fpart.write(body)
                            downloaded_checksum = self.glacier_instance.calculate_tree_hash(body, part_size)
                            fpart.close()
                            #print(downloaded_checksum)
                            
                            if response_checksum==downloaded_checksum:
                                #checksum is ok - write
                                print(part_index)
                                f = open(file_path_temp,'ab+')
                                f.write(body)
                                f.close()

                            #self.db.update_job(job_id, job_dict ,1)

                    import os
                    os.rename(file_path_temp, file_path_final)
                    # check archive checksum    
                    #downloaded_checksum = self.glacier_instance.calculate_tree_hash(open(file_path_final,'r').read(), size)
                    #print(archive_checksum)
                    #print(downloaded_checksum)
                    #if archive_checksum==downloaded_checksum:
                    #    print('ok')
                        
    def on_btn_request_download_job(self, button):
        archive = self.get_archive_from_data(self.obs_selected_archive.data)
        if archive:
            archive_id = archive['archiveid']
            
            # TO-DO: Create confirm dialog
            response = self.glacier_instance.initiate_archive_retrieval(self.obs_selected_vault.data, archive_id)
            self.db.create_job(self.obs_selected_vault.data, response.id, 'archive', archive_id=archive_id)

    def on_delete_vault(self, button):

        if not self.vaults_table.selected_row:
            self.main_window.error_dialog("Error", TEXT['ERROR_NOT_SELECTED_VAULT'])
            return None

        vaultname = self.vaults_table.selected_row['vaultname']
        numberofarchives = self.vaults_table.selected_row['numberofarchives']

        # check if vault has archvies.
        if numberofarchives > 0:
            self.main_window.error_dialog('Error', TEXT['ERROR_DELETE_VAULT_FILES'])
            return None
        
        # confirmation dialog
        msg = TEXT['DIALOG_DELETE_VAULT'] % (vaultname)
        response = self.main_window.confirm_dialog("Delete Vault", msg)
        if response:
            # execute task
            self._execute_bg_task(self.bg_delete_vault, vaultname=vaultname)

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
        # fetch data with threading
        self._execute_bg_task(self.bg_get_vaults_data)

    def on_upload_file(self, button):

        if not self.vaults_table.selected_row:
            self.main_window.error_dialog('Error', 'Vault Not selected')
            return None
        vaultname = self.vaults_table.selected_row['vaultname']

        inp = global_controls.get_control_by_name('Vaults_Upload_VaultPath')
        fullpath = inp.value
        if not fullpath:
            self.main_window.error_dialog('Error', 'File not selected')
            return None

        if fullpath and vaultname:
            self._execute_bg_task(self.bg_upload_file, vaultname=vaultname, fullpath=fullpath)

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
        option_3 = getattr(self, 'onprogress_box', None)
        option_4 = getattr(self, 'credentials_box', None)
        if option == option_2:
            self.select_option_vault_details()

    def select_option_vault_details(self):
        """ Actions after selecting Vault Detail Option
            - Get Pending Jobs
            - Populate Vault Archive Table
        """
        if not self.vaults_table.selected_row:
            return None

        selected_vault_name = self.vaults_table.selected_row['vaultname']

        self.obs_data_archives.data = []
        jobs = self.db.get_inventory_jobs(selected_vault_name)
        self.vault_pending_jobs.text = '%s %s' % (TEXT['PENDING_INVENTORY_JOBS'],str(len(jobs)))

        done_jobs = self.db.get_inventory_jobs(selected_vault_name, status='finished')
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
        self.refresh_vaults_button = toga.Button(TEXT['BTN_REFRESH_VAULTS'], on_press=self.on_refresh_vaults)
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
        self.vaults_table = Table(headers=HEADERS)
        self.vaults_table.subscribe('on_select_row', self.callback_row_selected)
        list_box.add(self.vaults_table.getbox())
        global_controls.add_from_controls(self.vaults_table.getcontrols(),'Vaults_TableContainer_')

        # Vaults -> Upload: Box
        add_file_box = toga.Box(style=Pack(direction=COLUMN, flex=1, padding_top=20))
        self.app_box.add(add_file_box)
        global_controls.add('Vaults_Upload', add_file_box.id)

        # Vaults -> Upload -> Title: Box
        upload_vault_title_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        add_file_box.add(upload_vault_title_box)
        global_controls.add('Vaults_Upload_Title', upload_vault_title_box.id)

        # Vaults -> Upload -> VaultName: Label
        upload_label = TEXT['LABEL_UPLOAD_VAULT'] % ('-')
        label_upload_vaultname = toga.Label(upload_label,style=STYLES['TITLE'])
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
        self.archives_table = Table(headers=HEADERS_ARCHIVES)
        self.archives_table.subscribe('on_select_row', self.callback_row_selected_archive)
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
        self.archive_selected_box._impl.set_hidden(False)

        # VaultDetail -> VaultTitle: Label
        self.archive_title = toga.Label('Archive selected: -', style=Pack(font_size=16, padding_bottom=1))
        self.archive_selected_box.add(self.archive_title)
        global_controls.add('VaultDetail_ArchiveTitle', self.archive_title.id)

        # VaultDetail -> PendingDownload: Label
        vault_pending_archive_down = toga.Label('%s 0' % (TEXT['PENDING_ARCHIVE_JOBS']))
        self.archive_selected_box.add(vault_pending_archive_down)
        global_controls.add('VaultDetail_PendingDownload', vault_pending_archive_down.id)

        # VaultDetail -> ArchiveDownloadBox: Box
        self.archive_download_box = toga.Box(style=Pack(direction=ROW, flex=1, padding_top=4))
        self.archive_selected_box.add(self.archive_download_box)
        global_controls.add('Vaults_ArchiveDownloadBox', self.archive_download_box.id)

        # VaultDetail -> StartDownloadArchiveJobButton: Button
        self.btn_request_download_job = toga.Button('Start Download Archive Job', on_press=self.on_btn_request_download_job)
        self.archive_download_box.add(self.btn_request_download_job)
        global_controls.add('VaultDetail_StartDownloadArchiveJobButton', self.btn_request_download_job.id)

        # VaultDetail -> StartDownloadArchiveJobButton: Button
        self.btn_download_archive = toga.Button('Download', on_press=self.on_btn_download_archive)
        self.archive_download_box.add(self.btn_download_archive)
        global_controls.add('VaultDetail_DownloadArchive', self.btn_download_archive.id)

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

        # OnProgress: Box
        self.onprogress_box = toga.Box(style=STYLES['OPTION_BOX'])
        global_controls.add('OnProgress', self.onprogress_box.id)
        
        # OnProgress > OnProgressTable: Table
        self.progress_table = Table(headers=HEADERS_ON_PROGRESS)
        #self.progress_table.subscribe('on_select_row', self.callback_row_selected)
        self.onprogress_box.add(self.progress_table.getbox())
        global_controls.add_from_controls(self.progress_table.getcontrols(),'OnProgress_TableContainer_')

        # Main -> OptionContainer: OptionContainer
        container = toga.OptionContainer(style=Pack(padding=10, direction=COLUMN), on_select=self.on_select_option)
        container.add('Vaults', self.app_box)
        container.add('Vault Detail', self.vault_box)
        container.add('On Progress', self.onprogress_box)
        container.add('Credentials', self.credentials_box)
        self.main_box.add(container)
        global_controls.add('Main_OptionContainer', container.id)

    def startup(self): 
        # setup
        self.pre_init()

        # Main: MainWindow
        self.main_window = toga.MainWindow(title="BeeGlacier", size=(800, 540))
        global_controls.set_window(self.main_window)

        # Main: Box
        self.main_box = toga.Box(style=Pack(direction=COLUMN, flex=1))
        global_controls.add('Main', self.main_box.id)

        # Create all controls
        self.create_controls()

        self._execute_bg_task(self.bg_tasks_checker)

        # Show Main Window
        self.main_window.content = self.main_box
        self.main_window.show()

        # ---
        # create observable for storing list of vaults
        self.obs_data_archives = ObsData()
        self.obs_data_archives.bind_to(self.obs_data_table_archives)

        self.obs_selected_archive = ObsData(None)
        self.obs_selected_archive.bind_to(self.obs_selected_archive_callback)

        # get last retrieve of vaults from database 
        vaults_db = self.db.get_vaults(self.account_id)
        if vaults_db:
            self.vaults_table.data = json.loads(vaults_db)

def main():
    return beeglacier()