import os
import optparse
import sys
import logging
import json
import requests
import time
from configparser import ConfigParser
from sftp_downloader import SftpDownloader
import version_config_generator
from data_checker import DataChecker
import post_process_kor

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT_DIR, "Cygnus", "config"))


class KORDownloader(object):
    def __init__(self, quarter, cygnus_component, mode):
        self.region = "KOR"
        self.quarter = quarter
        self.vendor = "{}_HERE_{}".format(self.region, self.quarter)
        self.downloader = SftpDownloader()
        self.cygnus_component = cygnus_component
        self.mode = mode
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config")
        self.history_file_name = ".download_history"
        self.cygnus_data_api_url = "http://cygnus.telenav.com/api/data"
        self.set_path()

    def set_path(self):
        config_file = os.path.join(self.config_path, "data_path.cfg")
        if not os.path.isfile(config_file):
            logging.error("Config file {} not found, exit program".format(config_file))
            sys.exit(-1)
        conf = ConfigParser()
        conf.read(config_file)
        self.main_data_path = os.path.join(conf.get("KOR", "local_path"), self.vendor)
        self.main_backup_path = os.path.join(conf.get("KOR", "s3_path"), self.vendor)

    def start(self):
        if self.mode != "check":
            self.download_packages()
            self.backup_packages()
        self.process_data()

    def download_packages(self):
        """Download KOR rdf data from remote machine."""
        year, quarter = version_config_generator.get_quarter_split(self.quarter)
        sftp_version = "Q{}{}".format(quarter, year)
        rdf_source_path = "/data/150_RDF_Core/{}".format(sftp_version)
        add_content_source_path = "/data/510_Additional_Contents/{}".format(sftp_version)
        if not self.downloader.isdir(rdf_source_path) or not self.downloader.isdir(add_content_source_path):
            logging.info("{} data is not ready, exit program".format(self.quarter))
            sys.exit(0)

        self.downloader.download_directory(rdf_source_path, self.main_data_path)
        self.downloader.download_directory(add_content_source_path, self.main_data_path)

    def backup_packages(self):
        """Backup KOR raw data to s3"""
        os.system("aws s3 sync {} {}".format(self.main_data_path, self.main_backup_path))

    def process_data(self):
        self.data_checker = DataChecker(self.region, self.quarter, self.main_data_path)
        with open(os.path.join(self.config_path, "kor_config.json"), 'r') as config_file:
            config_dict = json.load(config_file)
        for cygnus_component in config_dict:
            if self.cygnus_component and self.cygnus_component != cygnus_component:
                continue

            # Set package name for TOLLCOST in Cygnus
            if cygnus_component == "TOLLCOST":
                self.create_tollcost_data(config_dict[cygnus_component][0])
            else:
                self.create_cygnus_data(cygnus_component)

            for component in config_dict[cygnus_component]:
                if self.mode != "check" and not self.data_checker.is_component_downloaded(component, cygnus_component):
                    self.move_zip_file(component)
                    self.post_process(component)
                    self.create_cygnus_data_link(component, cygnus_component)
                self.data_checker.check_component(component, cygnus_component)
            self.update_cygnus_data_status(cygnus_component)

        self.data_checker.generate_main_report()
        os.chdir(self.main_data_path)  # Not affected
        os.system("rm *.zip;chmod -R 775 ./")

    def move_zip_file(self, component):
        zip_file_list = os.listdir(self.main_data_path)
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        os.makedirs(local_dir, exist_ok=True)
        for zip_file in zip_file_list:
            if zip_file.startswith(component["zip_name"]):
                os.system("mv {} {}/".format(os.path.join(self.main_data_path, zip_file), local_dir))
                os.system("echo \"{}|{}|{}\" >> {}".format(component["name"], zip_file,
                                                           time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                           os.path.join(self.main_data_path, self.history_file_name)))

    def post_process(self, component):
        if "post_process_method" not in component:
            return
        logging.info("Begin post process {} data".format(component["name"]))
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        os.chdir(local_dir)

        post_process_method = getattr(post_process_kor, component["post_process_method"])
        post_process_method()
        logging.info("Post process {} data done".format(component["name"]))

    def create_cygnus_data(self, cygnus_component):
        cygnus_data_name = "{}_{}".format(cygnus_component, self.vendor)
        cygnus_data_get_url = "{}/{}.json".format(self.cygnus_data_api_url, cygnus_data_name)
        cygnus_data_path = os.path.join(self.main_data_path, cygnus_component, cygnus_data_name)
        os.makedirs(cygnus_data_path, exist_ok=True)
        os.system("chmod 775 {}".format(cygnus_data_path))
        response = json.loads(requests.get(cygnus_data_get_url).content)
        if "data" not in response:
            requests.post(self.cygnus_data_api_url, {"path": cygnus_data_path,
                                                     "host": "ec5d-pbfcompilation-03.mypna.com"})

    def create_tollcost_data(self, tollcost_config):
        cygnus_data_name = "TOLLCOST_{}".format(self.vendor)
        s3_prefix = tollcost_config["s3_dir"]
        cygnus_data_path = os.path.join(s3_prefix, self.vendor, cygnus_data_name)
        cygnus_data_get_url = "{}/{}.json".format(self.cygnus_data_api_url, cygnus_data_name)
        response = json.loads(requests.get(cygnus_data_get_url).content)
        if "data" not in response:
            requests.post(self.cygnus_data_api_url, {"path": cygnus_data_path, "host": "s3://gmkorea-data"})
        for zip_file in os.listdir(self.main_data_path):
            if zip_file.startswith(tollcost_config["zip_name"]):
                os.system("aws s3 cp {} {}".format(os.path.join(self.main_data_path, zip_file),
                                                   os.path.join(cygnus_data_path, zip_file)))
                data_size = os.path.getsize(os.path.join(self.main_data_path, zip_file))
                requests.put(self.cygnus_data_api_url, {"path": cygnus_data_name, "tar_package_name": zip_file,
                                                        "data_size": data_size})

    def create_cygnus_data_link(self, component, cygnus_component):
        if "TOLLCOST" == cygnus_component:
            return
        cygnus_data_name = "{}_{}".format(cygnus_component, self.vendor)
        cygnus_data_dir = os.path.join(self.main_data_path, cygnus_component, cygnus_data_name,
                                       os.path.basename(component["local_dir"]))
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        if not os.path.isdir(cygnus_data_dir) and os.path.isdir(local_dir):
            os.system("ln -s {} {}".format(local_dir, cygnus_data_dir))

    def update_cygnus_data_status(self, cygnus_component):
        data_list = self.data_checker.main_result_info["cygnus_components"].get(cygnus_component, [])
        # For RAW-RDF+ data, we need to change status after prepare gemini raw data.
        # The status of RAW-RDF+ data is updated in Jenkins pipeline.
        if cygnus_component == "RAW-RDF+":
            return
        new_status = "released"
        for data in data_list:
            if data["status"] == self.data_checker.CHECK_STATUS_ERROR:
                new_status = "error"
                break
            elif data["status"] == self.data_checker.CHECK_STATUS_NOT_READY:
                new_status = "in-progress"
            elif data["status"] == self.data_checker.CHECK_STATUS_WARNING and new_status == "released":
                new_status = "success"

        cygnus_data_name = "{}_{}".format(cygnus_component, self.vendor)
        cygnus_data_get_url = "{}/{}.json".format(self.cygnus_data_api_url, cygnus_data_name)
        result = json.loads(requests.get(cygnus_data_get_url).content)
        if "data" not in result:
            logging.error("Data {} doesn't exist in Cygnus!".format(cygnus_data_name))
            return
        old_status = result["data"]["status"]
        if new_status != old_status:
            cygnus_data_path = os.path.join(self.main_data_path, cygnus_component, cygnus_data_name)
            if new_status == "released" and old_status != "success":
                requests.put(self.cygnus_data_api_url, {"path": cygnus_data_path, "status": "success"})
            requests.put(self.cygnus_data_api_url, {"path": cygnus_data_path, "status": new_status})


def main():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    parser = optparse.OptionParser()
    parser.add_option('-q', '--quarter', help='quarter name', dest='quarter')
    parser.add_option('-c', '--component', help='cygnus component', dest='cygnus_component')
    parser.add_option('-m', '--mode', help='running mode', dest='mode')  # if mode=check, skip download, only check
    options, args = parser.parse_args()

    if not options.quarter:
        logging.error("Quarter must be provided, exit program")
        logging.info("Example: python3 kor_downloader.py -q 22Q3")
        sys.exit(-1)

    kor_downloader = KORDownloader(options.quarter, options.cygnus_component, options.mode)
    kor_downloader.start()


if __name__ == "__main__":
    main()
