"""
Amazon Glacier Backups
----------------------
Icons made by Freepik" https://www.flaticon.com/authors/freepik
"""

import os
from pathlib import Path
import threading
import ntpath
import json
import tempfile

import toga
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

from .settings import (
    HEADERS,
    HEADERS_ARCHIVES,
    HEADERS_ON_PROGRESS,
    HEADERS_DOWNLOADS_JOBS,
    HEADERS_DOWNLOADS_CURRENT,
    HEADERS_JOBS
)
from .models.accounts import Account
from .models.deleted_archives import DeletedArchive
from .models.jobs import Job
from .models.uploads import Upload
from .models.vaults import Vault
from .components.form import Form
from .components.table import Table
from .utils import ObsData, Controls
from .utils.aws import Glacier
from .utils.strings import TEXT
from .utils.styles import STYLES
from .models.jobs import Job

global_controls = Controls()

class beeglacier(toga.App):

    glacier_instance = None
    vaults_table = None
    
    bgtasks = list()

    # observables datas
    obs_data_archives = None

    def _connect_glacier(self):
        aid, akey, skey, reg = Account.getaccount()
        if not self.glacier_instance:
            self.glacier_instance = Glacier(aid, akey, skey, reg)
        return self.glacier_instance

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

    def bg_get_vaults_data(self):
        # get account info and create glacier instance
        # In background task is necessary to do this
        glacier = self._connect_glacier()

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
        vault_db = Vault.insert(
            account_id = glacier.account_id,
            response = json.dumps(data)
        ).execute()

        # update table
        self.vaults_table.data = data

        # refresh UI
        self._update_control_label('Vaults_TopNav_RefreshVaults', 
                                   TEXT['BTN_REFRESH_VAULTS'])

    def bg_upload_file(self, *args, **kwargs):
        """ Background task for uploading files
        """

        if 'vaultname' not in kwargs or 'fullpath' not in kwargs:
            return

        vault = kwargs['vaultname']
        path = kwargs['fullpath']

        glacier = self._connect_glacier()

        filename = ntpath.basename(path)
        partsize = 4

        upload_id = glacier.create_multipart_upload(vault, filename, partsize)

        # TODO: change this insert for update. Check first if exist.
        uploaddb = Upload.insert({
            'account_id': glacier.account_id,
            'vault': vault,
            'upload_id': upload_id,
            'filepath': path
        }).execute()

        response = glacier.upload(vault, path, filename, partsize, 4, upload_id)

        update_upload = Upload.update(response = json.dumps(response)) \
                              .where(Upload.upload_id == upload_id).execute()

    def bg_delete_vault(self, *args, **kwargs):
        glacier = self._connect_glacier()
        
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

    def bg_delete_archive(self, *args, **kwargs):
        if 'vaultname' not in kwargs or 'archiveid' not in kwargs: 
            return 
        
        db = DB(DB_PATH)
        vaultname = kwargs['vaultname']
        archiveid = kwargs['archiveid']

        #delete file
        response = self.glacier_instance.delete_archive(vaultname, archiveid)
        DeletedArchive.insert({
            'vaultname': vaultname,
            'archiveid': archiveid,
            'response': json.dumps(response)
        }).execute()

    def bg_start_inv_job(self, vaultname):
        """ Start an inventory job and save response to db
        """
        res = self.glacier_instance.initiate_inventory_retrieval(vaultname)
        jobdb = Job.insert({
                'id': vaultname,
                'job_id': res.id,
                'job_type': 'inventory'
            }).execute()
        self.refresh_option_vault_details()

    def bg_check_jobs(self, vaultname):

        jobs = Job.select().where(
                    (Job.id == vaultname) &
                    (Job.done == 0)
                ).order_by(Job.created_at.desc()).execute()
        
        for job in jobs:
            job_id = job.job_id
            job_desc = self.glacier_instance.describe_job(vaultname, job_id)

            if not job_desc:
                # not controlled situation
                raise Exception('Something is wrong')

            if not job_desc['Completed']:
                print (f"Job {job_id} is not ready to download")
            
            if job_desc['StatusCode'] == 'Succeeded':
                # donwload job output
                r = self.glacier_instance.get_job_output(vaultname, job_id)
                if r['status'] == 200:
                    job_dict = json.loads(r['body'].read().decode())

                    jobdb = Job.update(
                            response = json.dumps(job_dict),
                            done = 0
                        ).where(Job.id == job_id).execute()

            elif job_desc['StatusCode'] == 'ResourceNotFound':
                # wrong ...
                pass 
            else:
                # job probably is expired (expires after 24 h I think)
                # Update database with Expired data 
                jobdb = Job.update(
                        response = json.dumps(job_desc),
                        done = 1,
                        error = 1
                    ).where(Job.id == job_id).execute()

        self.refresh_option_vault_details()

    def bg_update_progress_uploads(self, arg2):
        """ update progress_table """
        data = []
        if self.glacier_instance.current_uploads:
            for key, v in self.glacier_instance.current_uploads.items():
                print(key)
                print(v)
                porcentage = round(v['done']/v['total_parts']*100)
                progress = f'{porcentage}%'
                description = f'Uploading: {v["description"]}'
                data.append({'upload_id': key,'description': description, 'progress': progress})
        self.progress_table.data = data

    def callback_row_selected(self, row):
        """ Callback when vault row is selected
        """
        if not row:
            return

        # Update Labels
        selected_vault_text = TEXT['LABEL_SELECTED_VAULT'] % (row['vaultname'])
        self._update_control_label('VaultDetail_VaultTitle', selected_vault_text)
        upload_vault_text = TEXT['LABEL_UPLOAD_VAULT'] % (row['vaultname'])
        self._update_control_label('Vaults_Upload_VaultName', upload_vault_text)
        delete_vault_text = TEXT['BTN_DELETE_VAULT'] % (row['vaultname'])
        self._update_control_label('Vaults_TopNav_DeleteVault', delete_vault_text)
        delete_btn = global_controls.get_control_by_name('Vaults_TopNav_DeleteVault')
        delete_btn.enabled = True

    def callback_row_selected_archive(self, archive):
        if not archive:
            return

        text = TEXT['LABEL_SELECTED_ARCHIVE'] % (archive['archivedescription'])
        self._update_control_label('VaultDetail_ArchiveTitle', text)

        jobs = Job.select().where(
                (Job.archiveid == archive['archiveid']) &
                (Job.done == 0)
            ).execute()
        text = f'{TEXT["PENDING_ARCHIVE_JOBS"]}{len(jobs)}'
        self._update_control_label('VaultDetail_PendingDownload', text)    

    def callback_create_account(self, button):
        # called after pressed save button
        values = self.account_form.get_values()
        Account.saveaccount(values)

    def obs_data_table_archives(self, test):
        self.archives_table.data = self.obs_data_archives.data

    def get_archive_from_data(self, archivename):
        target_archive = list( filter(lambda x: x['archivedescription']==self.obs_selected_archive.data, self.obs_data_archives.data) )
        if target_archive:
            return target_archive[0]
        else:
            return None

    def on_btn_download_archive(self, button):
        #https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/glacier.html#Glacier.Client.get_job_output
        archive = self.get_archive_from_data(self.obs_selected_archive.data)
        file_path_temp = '/users/ignaciocabeza/downloads/' + self.obs_selected_archive.data + '.downloading'
        file_path_final = file_path = '/users/ignaciocabeza/downloads/' + self.obs_selected_archive.data

        vault = self.vaults_table.selected_row
        vaultname = vault['vaultname']

        if archive:
            jobs = Job.select().where(
                (Job.archiveid == archive['archiveid']) &
                (Job.done == 0)
            ).execute()

            if jobs:
                job_id = jobs[0].id
                
                job_description = self.glacier_instance.describe_job(vaultname, job_id)
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
                        job_result = self.glacier_instance.get_job_output(vaultname, job_id, range=param_range)
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

            vault = self.vaults_table.selected_row
            vaultname = vault['vaultname']
            
            # TO-DO: Create confirm dialog
            response = self.glacier_instance.initiate_archive_retrieval(vaultname, archive_id)
            jobdb = Job.insert({
                'vaultname': vaultname,
                'id': response.id,
                'job_type': 'archive',
                'archiveid': archive_id
            }).execute()

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
        msg = TEXT['DIALOG_DELETE'] % (vaultname)
        response = self.main_window.confirm_dialog("Delete Vault", msg)
        if response:
            # execute task
            self._execute_bg_task(self.bg_delete_vault, vaultname=vaultname)

    def on_delete_archive(self, button):

        if not self.archives_table.selected_row:
            self.main_window.error_dialog("Error", 
                                          TEXT['ERROR_NOT_SELECTED_ARCHIVE'])
            return None

        vaultname = self.vaults_table.selected_row['vaultname']
        archiveid = self.archives_table.selected_row['archiveid']
        description = self.archives_table.selected_row['archivedescription']

        # confirmation dialog
        msg = TEXT['DIALOG_DELETE'] % (description)
        response = self.main_window.confirm_dialog("Delete Archive", msg)
        if response:
            # execute task
            self._execute_bg_task(self.bg_delete_archive, 
                                  vaultname=vaultname,
                                  archiveid=archiveid)

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

    def on_btn_start_inv_job(self, button):
        vault_sel = self.vaults_table.selected_row
        if not vault_sel:
            return 
        vaultname = vault_sel['vaultname']
        self._execute_bg_task(self.bg_start_inv_job, vaultname)

    def on_btn_check_jobs(self, button):
        vault_sel = self.vaults_table.selected_row
        if not vault_sel:
            return 
        vaultname = vault_sel['vaultname']
        self._execute_bg_task(self.bg_check_jobs, vaultname)

    def on_select_option(self, interface, option):
        # Hack for rewriting UI and autoresizing controls
        option.refresh()

        # Actions triggered after selecting options
        option_vaults = getattr(self, 'app_box', None)
        option_details = getattr(self, 'vault_box', None)
        option_uploads = getattr(self, 'onprogress_box', None)
        option_downloads = getattr(self, 'downloads_box', None)
        option_jobs = getattr(self, 'jobs_box', None)
        option_settings = getattr(self, 'credentials_box', None)
        if option == option_details:
            self.refresh_option_vault_details()

    def on_pause_upload(self, button):
        selected_upload = self.progress_table.selected_row
        if 'upload_id' in selected_upload:    
            self.glacier_instance.send_pause_upload_signal(selected_upload['upload_id'])
    
    def on_resume_upload(self, button):
        selected_upload = self.progress_table.selected_row
        if 'upload_id' in selected_upload:    
            self.glacier_instance.send_pause_upload_signal(selected_upload['upload_id'])

    def refresh_option_vault_details(self):
        """ Actions after selecting Vault Detail Option
            - Get Pending Jobs
            - Populate Vault Archive Table
        """
        if not self.vaults_table.selected_row:
            return None

        selected_vault_name = self.vaults_table.selected_row['vaultname']

        self.obs_data_archives.data = []
        jobs = Job.select().where(
                    (Job.id == selected_vault_name) &
                    (Job.done == 0)
                  ).order_by(Job.created_at.desc()).execute()

        text_pend_jobs = f'{TEXT["PENDING_INVENTORY_JOBS"]} {len(jobs)}'
        self.vault_pending_jobs.text = text_pend_jobs

        done_jobs = Job.select().where(
                    (Job.id == selected_vault_name) &
                    (Job.done == 1) &
                    (Job.error == 0)
                  ).order_by(Job.created_at.desc()).execute()

        
        if len(done_jobs):
            last_job_done = json.loads(done_jobs[0].response)
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
        btn_start_inv_job = toga.Button(TEXT['BTN_START_INV_JOB'], 
                                        on_press=self.on_btn_start_inv_job)
        self.bottom_nav_vault.add(btn_start_inv_job)
        global_controls.add('VaultDetail_StartInventoryJobButton', 
                            btn_start_inv_job.id)

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

        # VaultDetail_DownloadArchive: Button
        self.btn_download_archive = toga.Button('Download', on_press=self.on_btn_download_archive)
        self.archive_download_box.add(self.btn_download_archive)
        global_controls.add('VaultDetail_DownloadArchive', self.btn_download_archive.id)

        # VaultDetail_DeleteArchive: Button
        self.btn_delete_archive = toga.Button('Delete', on_press=self.on_delete_archive)
        self.archive_download_box.add(self.btn_delete_archive)
        global_controls.add('VaultDetail_DeleteArchive', self.btn_delete_archive.id)

        # credentials
        fields = [
            {
                'name': 'account_id', 
                'label': 'Account ID:', 
                'validate': ['notnull'],
            },
            {
                'name': 'access_key', 
                'label': 'Access Key:', 
            },
            {
                'name': 'secret_key', 
                'label': 'Secret Key:', 
            },
            {
                'name': 'region_name', 
                'label': 'Region Name:', 
            },
        ]
        confirm = {
            'label': 'Save credentials', 
            'callback': self.callback_create_account 
        }
        
        self.account_form = Form(fields=fields, confirm=confirm, initial=Account.getaccount())
        self.credentials_box = self.account_form.getbox()
        global_controls.add_from_controls(self.account_form.getcontrols(),'Credentials_')

        # OnProgress: Box
        self.onprogress_box = toga.Box(style=STYLES['OPTION_BOX'])
        global_controls.add('OnProgress', self.onprogress_box.id)
        
        # OnProgress > OnProgressTable: Table
        self.progress_table = Table(headers=HEADERS_ON_PROGRESS)
        #self.progress_table.subscribe('on_select_row', self.callback_row_selected)
        self.onprogress_box.add(self.progress_table.getbox())
        global_controls.add_from_controls(self.progress_table.getcontrols(),'OnProgress_TableContainer_')

        # OnProgress_PauseUpload: Button
        self.btn_pause_upload = toga.Button('Pause', on_press=self.on_pause_upload)
        self.onprogress_box.add(self.btn_pause_upload)
        global_controls.add('OnProgress_PauseUpload', self.btn_pause_upload.id)

        # OnProgress_ResumeUpload: Button
        self.btn_resume_upload = toga.Button('Resume', on_press=self.on_resume_upload)
        self.onprogress_box.add(self.btn_resume_upload)
        global_controls.add('OnProgress_ResumeUpload', self.btn_resume_upload.id)

        # DownloadBox: Box (Inside Option Download)
        self.downloads_box = toga.Box(style=STYLES['OPTION_BOX'])
        global_controls.add('DownloadBox', self.downloads_box.id)

        # DownloadBox > TableJobs
        self.downloadjob_table = Table(headers=HEADERS_DOWNLOADS_JOBS)
        self.downloads_box.add(self.downloadjob_table.getbox())
        global_controls.add_from_controls(self.downloadjob_table.getcontrols(),'DownloadBox_TableJobs_')

        # DownloadBox > TableCurrent
        self.current_downloads_table = Table(headers=HEADERS_DOWNLOADS_CURRENT)
        self.downloads_box.add(self.current_downloads_table.getbox())
        global_controls.add_from_controls(self.current_downloads_table.getcontrols(),'DownloadBox_TableCurrent_')

        # JobsBox: Box (Inside Option Download)
        self.jobs_box = toga.Box(style=STYLES['OPTION_BOX'])
        global_controls.add('JobsBox', self.jobs_box.id)

        # Main -> OptionContainer: OptionContainer
        container = toga.OptionContainer(style=Pack(padding=10, direction=COLUMN), on_select=self.on_select_option)
        container.add('Vaults', self.app_box)
        container.add('Vault Detail', self.vault_box)
        container.add('Jobs', self.jobs_box)
        container.add('Uploads', self.onprogress_box)
        container.add('Downloads', self.downloads_box)
        container.add('Credentials', self.credentials_box)
        
        self.main_box.add(container)
        global_controls.add('Main_OptionContainer', container.id)
        
    def launch_bg_update_onprogress(self):
        """ launch a bg task for refresh UI. This is called by an
            observable inside Glacier Instance. Every time "current_uploads"
            change, this task is called
        """
        self.add_background_task(self.bg_update_progress_uploads)
    
    def pre_init(self):
        self.account = Account.getaccount(object)
        if not self.account:
            return False
        else:
            self.glacier_instance = Glacier(
                self.account.account_id, 
                self.account.access_key,
                self.account.secret_key, 
                self.account.region_name
            )

        # register an observable for current uploads status change
        self.glacier_instance.subscribe('current_uploads_change', 
                                        self.launch_bg_update_onprogress)

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

        #self._execute_bg_task(self.bg_tasks_checker)

        # Show Main Window
        self.main_window.content = self.main_box
        self.main_window.show()

        # ---
        # create observable for storing list of vaults
        self.obs_data_archives = ObsData()
        self.obs_data_archives.bind_to(self.obs_data_table_archives)

        # get last retrieve of vaults from database
        vaults_db = Vault.select() \
                         .where(Vault.account_id == self.account.account_id) \
                         .order_by(Vault.updated_at.desc()).limit(1).execute()
        if vaults_db:
            self.vaults_table.data = json.loads(vaults_db[0].response)

def main():
    return beeglacier()