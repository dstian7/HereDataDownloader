import optparse
import os
import json
import sys

import requests
import time
from configparser import ConfigParser
from http_downloader import HttpDownloader
from version_config_generator import *
import post_process
from data_checker import DataChecker


class GlobalDownloader:
    VERSION_TYPE_MONTHLY = "monthly"
    VERSION_TYPE_QUARTERLY = "quarterly"
    ACTION_TYPE_REUSE = "reuse"
    TYPE_TN_PRIVATE_LAYER = "tn_private_layer"

    def __init__(self, region, version, cygnus_component, mode):
        self.downloader = HttpDownloader()
        self.region = region
        self.version = version
        self.cygnus_component = cygnus_component
        self.mode = mode if mode else "all"
        self.vendor = "{}_HERE_{}".format(self.region, self.version)
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config")
        if is_month(self.version):
            self.config_file_name = "components_config_monthly.json"
            self.version_type = self.VERSION_TYPE_MONTHLY
        elif is_quarter(self.version):
            self.config_file_name = "components_config.json"
            self.version_type = self.VERSION_TYPE_QUARTERLY
        else:
            logging.error("Invalid version {}".format(self.version))
            sys.exit(-1)
        self.history_file_name = ".download_history"
        self.cygnus_data_api_url = "http://cygnus.telenav.com/api/data"
        self.set_path()
        self.data_checker = DataChecker(self.region, self.version, self.main_data_path)

    def set_path(self):
        config_file = os.path.join(self.config_path, "data_path.cfg")
        if not os.path.isfile(config_file):
            logging.error("Config file {} not found, exit program".format(config_file))
            sys.exit(-1)
        conf = ConfigParser()
        conf.read(config_file)
        self.main_data_path = os.path.join(conf.get("GLOBAL", "local_path"), self.vendor)
        self.s3_data_path = os.path.join(conf.get("GLOBAL", "s3_path"), self.vendor)
        self.main_doc_path = os.path.join(conf.get("GLOBAL", "doc_path"), self.version)
        self.latest_addcontent_path = os.path.join(conf.get("GLOBAL", "latest_addcontent_path"), self.region)

    def start(self):
        if self.version_type == self.VERSION_TYPE_QUARTERLY:
            self.start_quarterly()
        elif self.version_type == self.VERSION_TYPE_MONTHLY:
            self.start_monthly()

    def start_quarterly(self):
        with open(os.path.join(self.config_path, self.config_file_name), 'r') as config_file:
            config_dict = json.load(config_file)
        if self.region not in config_dict:
            logging.error("Invalid region {}".format(self.region))
            sys.exit(-1)
        overall_status = HttpDownloader.DOWNLOAD_STATUS_SKIPPED

        for cygnus_component in config_dict[self.region]:
            if self.cygnus_component and self.cygnus_component != cygnus_component:
                continue
            self.create_cygnus_data(cygnus_component)
            for component in config_dict[self.region][cygnus_component]:
                if self.mode != "check" and not self.data_checker.is_component_downloaded(component, cygnus_component):
                    download_status = self.download_quarterly(component)
                    if download_status == HttpDownloader.DOWNLOAD_STATUS_SUCCESS:
                        overall_status = HttpDownloader.DOWNLOAD_STATUS_SUCCESS
                        self.post_process(component)
                    self.create_cygnus_data_link(component, cygnus_component)
                self.data_checker.check_component(component, cygnus_component, self.version)
            self.update_cygnus_data_status(cygnus_component)

        self.data_checker.generate_main_report()
        os.system("chmod -R 775 {}".format(self.main_data_path))
        if overall_status == HttpDownloader.DOWNLOAD_STATUS_SUCCESS:
            os.system('aws s3 sync {} {} --exclude "RAW*"'.format(
                self.main_data_path, self.s3_data_path))

    def start_monthly(self):
        with open(os.path.join(self.config_path, self.config_file_name), 'r') as config_file:
            config_dict = json.load(config_file)
        if self.region not in config_dict:
            logging.error("Invalid region {}".format(self.region))
            sys.exit(-1)

        cygnus_data_name = "{}_{}".format("RAW-RDF+", self.vendor)
        cygnus_data_get_url = "{}/{}.json".format(self.cygnus_data_api_url, cygnus_data_name)
        response = json.loads(requests.get(cygnus_data_get_url).content)
        if "data" in response:
            if response["data"]["status"] in ["released", "success"]:
                logging.error("raw data for {} {} has been downloaded, exit program".format(self.region,
                                                                                            self.version))
                sys.exit(-1)

        rdf_ready = False
        self.create_cygnus_data("RAW-RDF+")
        for component in config_dict[self.region]["RAW-RDF+"]:
            if "rdf" in component["name"]:
                if not self.data_checker.is_component_downloaded(component, "RAW-RDF+"):
                    self.download_monthly(component)
                    self.create_cygnus_data_link(component, "RAW-RDF+")
                check_pass = self.data_checker.check_component(component, "RAW-RDF+", self.version)
                if check_pass:
                    rdf_ready = True
        if rdf_ready:
            for cygnus_component in config_dict[self.region]:
                self.create_cygnus_data(cygnus_component)
                for component in config_dict[self.region][cygnus_component]:
                    if "rdf" in component["name"]:
                        continue
                    if not self.data_checker.is_component_downloaded(component, cygnus_component):
                        download_version = self.download_monthly(component)
                        self.create_cygnus_data_link(component, cygnus_component)
                        self.data_checker.check_component(component, cygnus_component, download_version)
                self.update_cygnus_data_status(cygnus_component)
            self.data_checker.generate_main_report()
            os.system("chmod -R 775 {}".format(self.main_data_path))
            os.system('aws s3 sync {} {} --exclude "RAW*"'.format(self.main_data_path, self.s3_data_path))

    def create_cygnus_data(self, cygnus_component):
        cygnus_data_name = "{}_{}".format(cygnus_component, self.vendor)
        cygnus_data_get_url = "{}/{}.json".format(self.cygnus_data_api_url, cygnus_data_name)
        cygnus_data_path = os.path.join(self.main_data_path, cygnus_component, cygnus_data_name)
        os.makedirs(os.path.dirname(cygnus_data_path), exist_ok=True)
        os.system("chmod 775 {}".format(os.path.dirname(cygnus_data_path)))
        response = json.loads(requests.get(cygnus_data_get_url).content)
        if "data" not in response:
            requests.post(self.cygnus_data_api_url, {"path": cygnus_data_path})
        report_link = "https://tact.telenav.com/data/{}/check_report/result_report.html".format(self.vendor)
        requests.put("{}/{}".format(self.cygnus_data_api_url, cygnus_data_name), {"report_link": report_link})

    def create_cygnus_data_link(self, component, cygnus_component):
        # For EU traffic location, skip 3rd party data
        if component["name"] == "traffic_location" and not component["local_dir"].endswith("traffic_location"):
            return
        cygnus_data_name = "{}_{}".format(cygnus_component, self.vendor)
        cygnus_data_dir = os.path.join(self.main_data_path, cygnus_component, cygnus_data_name)
        if cygnus_component in ["RAW-RDF+", "RAW-JUNCTION"]:
            cygnus_data_dir = os.path.join(cygnus_data_dir, os.path.basename(str(component["local_dir"])))
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        if not os.path.isdir(cygnus_data_dir) and os.path.isdir(local_dir):
            os.makedirs(os.path.dirname(cygnus_data_dir), exist_ok=True)
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

    def download_quarterly(self, component):
        if "here_product" not in component or "here_release" not in component:
            return HttpDownloader.DOWNLOAD_STATUS_SKIPPED
        if "type" in component and component["type"] == self.TYPE_TN_PRIVATE_LAYER:
            return self.download_tn_private_layer(component)
        if self.region == "EU" and component["name"] == "traffic_location":
            misc_dir = "/var/www/html/data/MISC/EU_Location/{}".format(self.version)
            if not os.path.isdir(misc_dir):
                logging.info("3rd party traffic location table not ready, skip download")
                return HttpDownloader.DOWNLOAD_STATUS_SKIPPED
        is_standalone = component.get("standalone_version", "") == "True"
        rdf_version, add_version, add_full_version = get_version(self.version, is_standalone)
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        version = rdf_version if "rdf" in component["name"] else add_version
        for release in component["here_release"]:
            release_name = release if "rdf" in component["name"] else "{} {}".format(release, add_full_version)
            status = self.downloader.download_data(component["here_product"], release_name, version, local_dir)
            if status != HttpDownloader.DOWNLOAD_STATUS_SUCCESS:
                return status

            # Update download history file
            os.system("echo \"{}|{}|{}\" >> {}".format(component["name"], release,
                                                       time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                       os.path.join(self.main_data_path, self.history_file_name)))
        return HttpDownloader.DOWNLOAD_STATUS_SUCCESS

    def download_monthly(self, component):
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        if "action" in component and component["action"] == self.ACTION_TYPE_REUSE:
            reuse_version = self.get_reuse_version(component)
            reuse_dir = local_dir.replace(self.version, reuse_version)
            if not os.path.isdir(local_dir):
                os.makedirs(local_dir)
            logging.info("cp -r {}/* {}/".format(reuse_dir, local_dir))
            os.system("cp -r {}/* {}/".format(reuse_dir, local_dir))
            os.system("echo \"{}|{}|{}\" >> {}".format(component["name"], component["name"],
                                                       time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                       os.path.join(self.main_data_path, self.history_file_name)))
            return reuse_version
        elif "type" in component and component["type"] == self.TYPE_TN_PRIVATE_LAYER:
            self.download_tn_private_layer(component)
            return self.version
        elif get_rdf_quarter(self.version):
            quarter_version = get_rdf_quarter(self.version)
            quarterly_data_path = self.main_data_path.replace(self.version, quarter_version)
            quarterly_data_checker = DataChecker(self.region, quarter_version, quarterly_data_path)
            if quarterly_data_checker.is_component_downloaded(component, "RAW-RDF+"):
                quarterly_dir = os.path.join(quarterly_data_path, component["local_dir"])
                os.system("ln -sfn {} {}".format(quarterly_dir, local_dir))
            return quarter_version
        else:
            if "here_product" not in component or "here_release" not in component:
                return self.version
            rdf_version, rdf_full_version = get_monthly_version(self.version)
            for release in component["here_release"]:
                release_name = release.format(v=rdf_version)
                self.downloader.download_data(component["here_product"], release_name, rdf_full_version, local_dir)

                # Update download history file
                os.system("echo \"{}|{}|{}\" >> {}".format(component["name"], release,
                                                           time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                                                           os.path.join(self.main_data_path, self.history_file_name)))

            return self.version

    def download_tn_private_layer(self, component):
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        remote_s3_dir = component["raw_data_dir"]
        os.system("mkdir -p {}".format(local_dir))
        os.system("aws s3 cp {} {} --recursive".format(remote_s3_dir, local_dir))

    def get_reuse_version(self, component):
        default_version = get_base_quarter(self.version)
        if "gjv" in component["name"]:
            default_version = get_jv_quarter(self.version)
        if DataChecker.component_ready(component, self.main_data_path.replace(self.version, default_version)):
            logging.info("Reuse data from version {} for component {}".format(default_version, component["name"]))
            return default_version
        else:
            prev_version = get_previous_version(default_version)
            if DataChecker.component_ready(component, self.main_data_path.replace(self.version, prev_version)):
                logging.warning("Reuse data from version {} for component {}".format(prev_version, component["name"]))
                return prev_version
            else:
                logging.error("No available version to reuse for component {}".format(component["name"]))
                sys.exit(-1)

    def post_process(self, component):
        if "post_process_method" not in component:
            return
        logging.info("Begin post process {} data".format(component["name"]))
        local_dir = os.path.join(self.main_data_path, component["local_dir"])
        doc_dir = os.path.join(self.main_doc_path, component["name"], self.region)
        os.makedirs(doc_dir, exist_ok=True)
        os.chdir(local_dir)

        post_process_method = getattr(post_process, component["post_process_method"])
        post_process_method(doc_dir)
        logging.info("Post process {} data done".format(component["name"]))


def main():
    logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
    parser = optparse.OptionParser()
    parser.add_option('-r', '--region', help='region', dest='region')
    parser.add_option('-v', '--version', help='quarter name', dest='version')
    parser.add_option('-c', '--component', help='cygnus component', dest='cygnus_component')
    parser.add_option('-m', '--mode', help='running mode', dest='mode')  # if mode=check, skip download, only check
    options, args = parser.parse_args()

    if not options.region or not options.version:
        logging.error("Region and Version must be provided, exit program")
        logging.info("Example: python3 global_downloader.py -r EU -v 22Q3")
        sys.exit(-1)

    global_downloader = GlobalDownloader(options.region, options.version, options.cygnus_component, options.mode)
    global_downloader.start()


if __name__ == "__main__": # pragma: no cover
    main()
