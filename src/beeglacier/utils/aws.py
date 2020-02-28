import binascii
import concurrent.futures
import hashlib
import math
import os.path
import sys
import tarfile
import tempfile
import threading
import boto3

MAX_ATTEMPTS = 10
fileblock = threading.Lock()

"""
Info:
    - list of prices.
    - https://a0.p.awsstatic.com/pricing/1.0/glacier/index.json?timestamp=1581568546394
"""

class Glacier():

    # 
    """
    Current Upload structure:
    {
        'IDUPLOAD': {
            'description': 'test.zip', 
            'uploading': 10, 
            'status': 'UPLOADING', 
            'total_parts':12, 
            'done': 2
        }
    }
    """
    current_uploads = {}

    def __init__(self, account_id, access_key_id, 
                 secret_access_key, region_name):
        self.access_key_id = access_key_id
        self.account_id = account_id
        self.secret_access_key = secret_access_key
        self.region_name = region_name

        # maintain state of current uploads
        self.current_uploads = {}

    def _get_resource(self):
        """ get session or create a new one if does not exists
            Returns a glacier resource.
        """

        try:
            self.session = getattr(self,'session')
        except AttributeError:
            self.session = boto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region_name
            )

        return self.session.resource('glacier')

    def _get_client(self):

        try:
            self.client = getattr(self,'client')
        except AttributeError:
            self.client = boto3.client('glacier', 
                                    region_name=self.region_name,
                                    aws_access_key_id=self.access_key_id,
                                    aws_secret_access_key=self.secret_access_key)
        
        return self.client

    def get_archive(self, vault_name, archive_id):
        return self._get_resource().Archive(self.account_id , vault_name, archive_id)

    def get_vault(self, vault_name):
        return self._get_resource().Vault(self.account_id , vault_name)

    def create_vault(self, vault_name):
        return self._get_client().create_vault(vaultName=vault_name)

    def delete_vault(self, vault_name):
        return self._get_client().delete_vault(vaultName=vault_name)

    def list_vaults(self, marker=None):
        if marker:
            vaults = self._get_client().list_vaults(marker=marker)
        else:
            vaults = self._get_client().list_vaults()
        return vaults

    def exists_vault(self, vault_name):
        return self.get_vault(vault_name)

    def initiate_inventory_retrieval(self, vault_name):
        return self.get_vault(vault_name).initiate_inventory_retrieval()

    def initiate_archive_retrieval(self, vault_name, archive_id):
        return self.get_archive(vault_name, archive_id).initiate_archive_retrieval()

    def get_job_output(self, vault_name, job_id, range = None):
        if range:
            return self._get_client().get_job_output(vaultName=vault_name, jobId=job_id, range=range)
        else:
            return self._get_client().get_job_output(vaultName=vault_name, jobId=job_id)
        
    def describe_job(self, vault_name, job_id):
        return self._get_client().describe_job(vaultName=vault_name, jobId=job_id)

    def list_jobs(self, vault_name):
        return self._get_client().list_jobs(vaultName=vault_name)

    def delete_archive(self, vault_name, archive_id):
        return self._get_client().delete_archive(vaultName=vault_name, archiveId=archive_id)

    def upload_archive(self, vault_name, description, archive):
        return self.get_vault(vault_name).upload_archive(
            archiveDescription=description,
            body=archive,
        )

    def create_multipart_upload(self, vault_name, arc_desc, part_size):

        part_size = part_size * 1024 * 1024

        response = self._get_client().initiate_multipart_upload(
            vaultName=vault_name,
            archiveDescription=arc_desc,
            partSize=str(part_size)
        )

        new_upload_info = {
            'description': arc_desc,
            'status':'NOT_STARTED',
            'total_parts': 0, 
            'uploading': 0, 
            'done': 0
        }

        self.current_uploads[response['uploadId']] = new_upload_info
        return response['uploadId']

    def upload(self, vault_name, file_name, arc_desc, part_size, num_threads, upload_id):
        self.glacier = self._get_client()
        
        if not math.log2(part_size).is_integer():
            raise ValueError('part-size must be a power of 2')
        if part_size < 1 or part_size > 4096:
            raise ValueError('part-size must be more than 1 MB '
                             'and less than 4096 MB')

        print('Reading file...')
        if os.path.isdir(file_name):
            print('Tarring file...')
            file_to_upload = tempfile.TemporaryFile()
            tar = tarfile.open(fileobj=file_to_upload, mode='w:xz')
            for filename in file_name:
                tar.add(filename)
            tar.close()
            print('File tarred.')
        else:
            file_to_upload = open(file_name, mode='rb')
            print('Opened single file.')

        part_size = part_size * 1024 * 1024

        file_size = file_to_upload.seek(0, 2)

        if file_size < 4096:
            print('File size is less than 4 MB. Uploading in one request...')

            response = self.glacier.upload_archive(
                vaultName=vault_name,
                archiveDescription=arc_desc,
                body=file_to_upload)

            self.current_uploads[upload_id]['status'] = 'FINISHED'
            self.current_uploads[upload_id]['total_parts'] = 1
            self.current_uploads[upload_id]['uploading'] = 0
            self.current_uploads[upload_id]['done'] = 1 
            print('Uploaded.')
            print('Glacier tree hash: %s' % response['checksum'])
            print('Location: %s' % response['location'])
            print('Archive ID: %s' % response['archiveId'])
            print('Done.')
            file_to_upload.close()
            return

        job_list = []
        list_of_checksums = []

        if upload_id is None:
            print('Initiating multipart upload...')
            response = self.glacier.initiate_multipart_upload(
                vaultName=vault_name,
                archiveDescription=arc_desc,
                partSize=str(part_size)
            )
            upload_id = response['uploadId']

            for byte_pos in range(0, file_size, part_size):
                job_list.append(byte_pos)
                list_of_checksums.append(None)

            num_parts = len(job_list)
            print('File size is {} bytes. Will upload in {} parts.'.format(file_size, num_parts))
        else:
            print('Resuming upload...')

            print('Fetching already uploaded parts...')
            response = self.glacier.list_parts(
                vaultName=vault_name,
                uploadId=upload_id
            )
            parts = response['Parts']
            part_size = response['PartSizeInBytes']
            while 'Marker' in response:
                print('Getting more parts...')
                response = self.glacier.list_parts(
                    vaultName=vault_name,
                    uploadId=upload_id,
                    marker=response['Marker']
                )
                parts.extend(response['Parts'])

            for byte_pos in range(0, file_size, part_size):
                job_list.append(byte_pos)
                list_of_checksums.append(None)

            num_parts = len(job_list)
            
            for part_data in parts:
                byte_start = int(part_data['RangeInBytes'].partition('-')[0])
                file_to_upload.seek(byte_start)
                part = file_to_upload.read(part_size)
                checksum = self.calculate_tree_hash(part, part_size)

                if checksum == part_data['SHA256TreeHash']:
                    job_list.remove(byte_start)
                    part_num = byte_start // part_size
                    list_of_checksums[part_num] = checksum

        self.current_uploads[upload_id]['status'] = 'UPLOADING'
        self.current_uploads[upload_id]['total_parts'] = num_parts

        print('Spawning threads...')
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=num_threads) as executor:
            futures_list = {executor.submit(
                self.upload_part, job, vault_name, upload_id, part_size, file_to_upload,
                file_size, num_parts): job // part_size for job in job_list}
            done, not_done = concurrent.futures.wait(
                futures_list, return_when=concurrent.futures.FIRST_EXCEPTION)
            if len(not_done) > 0:
                # an exception occured
                for future in not_done:
                    future.cancel()
                for future in done:
                    e = future.exception()
                    if e is not None:
                        print('Exception occured: %r' % e)
                print('Upload not aborted. Upload id: %s' % upload_id)
                print('Exiting.')
                file_to_upload.close()
                sys.exit(1)
            else:
                # all threads completed without raising
                for future in done:
                    job_index = futures_list[future]
                    list_of_checksums[job_index] = future.result()

        if len(list_of_checksums) != num_parts:
            print('List of checksums incomplete. Recalculating...')
            list_of_checksums = []
            for byte_pos in range(0, file_size, part_size):
                part_num = int(byte_pos / part_size)
                print('Checksum %s of %s...' % (part_num + 1, num_parts))
                file_to_upload.seek(byte_pos)
                part = file_to_upload.read(part_size)
                list_of_checksums.append(self.calculate_tree_hash(part, part_size))

        total_tree_hash = self.calculate_total_tree_hash(list_of_checksums)

        print('Completing multipart upload...')
        response = self.glacier.complete_multipart_upload(
            vaultName=vault_name, uploadId=upload_id,
            archiveSize=str(file_size), checksum=total_tree_hash)
        print('Upload successful.')
        print('Calculated total tree hash: %s' % total_tree_hash)
        print('Glacier total tree hash: %s' % response['checksum'])
        print('Location: %s' % response['location'])
        print('Archive ID: %s' % response['archiveId'])
        print('Done.')
        self.current_uploads[upload_id]['status'] = 'FINISHED'
        file_to_upload.close()
        return response

    def upload_part(self, byte_pos, vault_name, upload_id, part_size, fileobj, file_size,
                    num_parts):
        fileblock.acquire()
        fileobj.seek(byte_pos)
        part = fileobj.read(part_size)
        fileblock.release()

        range_header = 'bytes {}-{}/{}'.format(
            byte_pos, byte_pos + len(part) - 1, file_size)
        part_num = byte_pos // part_size
        percentage = part_num / num_parts

        self.current_uploads[upload_id]['uploading'] += 1 
        print('Uploading part {0} of {1}... ({2:.2%})'.format(
            part_num + 1, num_parts, percentage))

        for i in range(MAX_ATTEMPTS):
            try:
                response = self.glacier.upload_multipart_part(
                    vaultName=vault_name, uploadId=upload_id,
                    range=range_header, body=part)
                checksum = self.calculate_tree_hash(part, part_size)
                if checksum != response['checksum']:
                    print('Checksums do not match. Will try again.')
                    continue

                # if everything worked, then we can break
                break
            except: 
                print('Upload error:', sys.exc_info()[0])
                print('Trying again. Part {0}'.format(part_num + 1))
        else:
            print('After multiple attempts, still failed to upload part')
            print('Exiting.')
            sys.exit(1)

        self.current_uploads[upload_id]['uploading'] -= 1
        self.current_uploads[upload_id]['done'] += 1
        del part
        return checksum

    def calculate_tree_hash(self, part, part_size):
        checksums = []
        upper_bound = min(len(part), part_size)
        step = 1024 * 1024  # 1 MB
        for chunk_pos in range(0, upper_bound, step):
            chunk = part[chunk_pos:chunk_pos+step]
            checksums.append(hashlib.sha256(chunk).hexdigest())
            del chunk
        return self.calculate_total_tree_hash(checksums)

    def calculate_total_tree_hash(self,list_of_checksums):
        tree = list_of_checksums[:]
        while len(tree) > 1:
            parent = []
            for i in range(0, len(tree), 2):
                if i < len(tree) - 1:
                    part1 = binascii.unhexlify(tree[i])
                    part2 = binascii.unhexlify(tree[i + 1])
                    parent.append(hashlib.sha256(part1 + part2).hexdigest())
                else:
                    parent.append(tree[i])
            tree = parent
        return tree[0]