import optparse
import json
import logging
import sys
import requests
from configparser import ConfigParser
from http_downloader import HttpDownloader
import version_config_generator
from ai_doc_summarizer import *


class DocDownloader:
    def __init__(self, quarter):
        self.quarter = quarter
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config")
        self.downloader = HttpDownloader()
        self.set_path()
        rdf_version, add_version, add_full_version = version_config_generator.get_version(self.quarter)
        self.doc_version = add_version
        self.doc_full_version = add_full_version
        with open(os.path.join(self.config_path, "doc_config.json"), 'r') as config_file:
            self.config_dict = json.load(config_file)

    def set_path(self):
        config_file = os.path.join(self.config_path, "data_path.cfg")
        if not os.path.isfile(config_file):
            logging.error("Config file {} not found, exit program".format(config_file))
            sys.exit(-1)
        conf = ConfigParser()
        conf.read(config_file)
        self.main_doc_path = conf.get("GLOBAL", "doc_path")

    def start(self):
        self.download_ctrg()
        self.download_release_notes()
        self.download_tnm()
        self.download_product_available_dates()

    def download_release_notes(self):
        release_note_items = self.config_dict["release_note"]
        file_version = version_config_generator.get_normal_file_version(self.quarter)
        for item in release_note_items:
            release_note_dir = os.path.join(self.main_doc_path, self.quarter, item["local_dir"])
            os.makedirs(release_note_dir, exist_ok=True)
            os.chdir(release_note_dir)
            files_count = int(os.popen("ls -l | grep -c pdf").read().strip())
            if files_count >= 1:
                logging.info("{} exists, skip download".format(item["here_release"]))
                continue
            release_name = "{} {}".format(item["here_release"], self.doc_version)
            status = self.downloader.download_data(item["here_product"], release_name, self.doc_version,
                                                   release_note_dir)
            if status == HttpDownloader.DOWNLOAD_STATUS_SUCCESS:
                self.__post_release_notes_download(file_version, release_note_dir)

    @staticmethod
    def __post_release_notes_download(file_version, release_note_dir):
        for f in os.listdir():
            if f.endswith(".tar"):
                if file_version not in f:
                    os.system("rm {}".format(f))
                else:
                    os.system("tar -xvf {}".format(f))
        os.system("rm -rf POI_Frequency;rm -rf POI_Frequency_Report")
        if os.path.isdir("Release_Notes"):
            os.system("mv Release_Notes/* ./")
            os.system("rm -rf Release_Notes")
        os.system("chmod -R 775 {}".format(release_note_dir))

    def download_ctrg(self):
        ctrg_item = self.config_dict["ctrg"]
        ctrg_dir = os.path.join(self.main_doc_path, self.quarter, ctrg_item["local_dir"])
        os.makedirs(ctrg_dir, exist_ok=True)
        ctrg_files_count = len(os.listdir(ctrg_dir))
        if ctrg_files_count >= 10:
            logging.info("CTRG exists, skip download")
            return
        release_name = "{} {}".format(ctrg_item["here_release"], self.doc_full_version)
        status = self.downloader.download_data(ctrg_item["here_product"], release_name, self.doc_version, ctrg_dir)
        if status == HttpDownloader.DOWNLOAD_STATUS_SUCCESS:
            os.chdir(ctrg_dir)
            os.system("for tarfile in *.tar; do tar xvf $tarfile; done")
            os.system("rm *.tar")
            os.system("chmod -R 775 {}".format(ctrg_dir))

    def download_tnm(self):
        self.create_cygnus_tnm_node()
        tnm_item = self.config_dict["tnm"]
        tnm_dir = os.path.join(self.main_doc_path, tnm_item["local_dir"])
        current_tnm_list = os.listdir(tnm_dir)
        current_tnm_list.sort()
        latest_folder = current_tnm_list[-1]
        if any(file.lower().endswith('.pdf') for file in os.listdir(os.path.join(tnm_dir, latest_folder))):
            download_number = int(latest_folder.split('-')[1]) + 1
        else:
            download_number = int(latest_folder.split('-')[1])
        tnm_name = "TNM-{}".format(download_number)
        logging.info("Download {}".format(tnm_name))
        tnm_dir = os.path.join(tnm_dir, tnm_name)
        os.system("mkdir -p {}".format(tnm_dir))
        release_name = "{}_0{}".format(tnm_item["here_release"], download_number)
        status = self.downloader.download_data(tnm_item["here_product"], release_name, self.doc_version, tnm_dir)
        if status == HttpDownloader.DOWNLOAD_STATUS_SUCCESS:
            os.chdir(tnm_dir)
            os.system("for tarfile in *.tar; do tar xvf $tarfile; done")
            os.system("chmod -R 775 {}".format(tnm_dir))
            for file_name in os.listdir():
                if file_name.startswith("AAAM") and "tar" not in file_name:
                    os.system("mv {}/* ./".format(file_name))
                    os.system("rm -rf {}".format(file_name))
                    break
            for file_name in os.listdir(tnm_name):
                if file_name.endswith(".pdf"):
                    os.system("mv '{}' ./{}.pdf".format(os.path.join(tnm_name, file_name), tnm_name))
                    break
            os.system("rm -rf {}".format(tnm_name))
            os.system("rm -rf *.tar")
            summarize_tnm(tnm_dir)
        else:
            os.system("rm -rf {}".format(tnm_dir))

    def create_cygnus_tnm_node(self):
        tnm_region_list = ["ANZ", "EU", "HKM", "ISC", "KOR", "MEA", "NA", "PAK", "SA", "SEA", "TWN"]
        cygnus_component = "TNM-REVIEW"
        cygnus_data_api_url = "http://cygnus.telenav.com/api/data"
        for region in tnm_region_list:
            tnm_vendor = "{}_HERE_{}".format(region, self.quarter)
            cygnus_data_name = "{}_{}".format(cygnus_component, tnm_vendor)
            cygnus_data_specific_url = "{}/{}".format(cygnus_data_api_url, cygnus_data_name)
            response = json.loads(requests.get(cygnus_data_specific_url + ".json").content)
            report_html = "http://tnavmapdata.s3-website.us-west-2.amazonaws.com/TNM/HERE/{}/report/html/index.html".format(
                self.quarter)
            if "data" not in response:
                report_link = "{}?region={}".format(report_html, region)
                requests.post(cygnus_data_api_url, {"region": region, "vendor": "HERE", "component": "TNM-REVIEW",
                                                    "version": self.quarter, "name": cygnus_data_name})
                requests.put(cygnus_data_specific_url, {"report_link": report_link})
            response = requests.head(report_html, timeout=5)
            report_exist = response.status_code == 200
            if report_exist:
                requests.put(cygnus_data_specific_url, {"status": "success"})
                requests.put(cygnus_data_specific_url, {"status": "released"})

    def download_product_available_dates(self):
        pad_item = self.config_dict["product_available_dates"]
        pad_dir = os.path.join(self.main_doc_path, pad_item["local_dir"])
        year, quarter_num = version_config_generator.get_last_quarter_split(self.quarter)
        start_quarter = "Q{}'{}".format(quarter_num, year)
        end_quarter = "Q{}'{}".format(quarter_num, year + 1)
        release_name = "{} - {} Product Availability Dates".format(start_quarter, end_quarter)
        status = self.downloader.download_data(pad_item["here_product"], release_name, self.doc_version, pad_dir)
        if status == HttpDownloader.DOWNLOAD_STATUS_SUCCESS:
            os.chdir(pad_dir)
            os.system("for tarfile in *.tar; do tar xvf $tarfile; done")
            os.system("chmod 775 *")


def main():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    parser = optparse.OptionParser()
    parser.add_option('-v', '--version', help='version name', dest='version')
    options, args = parser.parse_args()

    if not options.version:
        logging.error("Version must be provided, exit program")
        logging.info("Example: python3 doc_downloader.py -v 22Q3")
        sys.exit(-1)

    doc_downloader = DocDownloader(options.version)
    doc_downloader.start()


if __name__ == "__main__":
    main()
