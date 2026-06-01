import logging
import paramiko
import stat
import os
import sys


class SftpDownloader(object):
    def __init__(self,
                 sftp_host = "kor-download.ext.here.com",
                 sftp_port = 7222,
                 sftp_user = "telenav",
                 sftp_password = "GT2r7qTlRUadYM"):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(sftp_host, sftp_port, sftp_user, sftp_password, timeout=5)
        self.sftp = self.ssh.open_sftp()

    def __del__(self):
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()

    def isdir(self, dir_path):
        try:
            return stat.S_ISDIR(self.sftp.stat(dir_path).st_mode)
        except:
            return False

    def download_file(self, src_file, dest_dir):
        dest_file = os.path.join(dest_dir, os.path.basename(src_file))
        try:
            self.sftp.get(src_file, dest_file)
        except IOError as e:
            logging.error("Error: {}".format(e))
        logging.info("Download file {} to {} done".format(src_file, dest_file))

    def download_directory(self, src_dir, dest_dir):
        os.makedirs(dest_dir, exist_ok=True)
        for file_name in self.sftp.listdir(src_dir):
            src_file_path = os.path.join(src_dir, file_name)
            if stat.S_ISDIR(self.sftp.stat(src_file_path).st_mode):
                self.download_directory(src_file_path, os.path.join(dest_dir, file_name))
            else:
                self.download_file(src_file_path, dest_dir)
