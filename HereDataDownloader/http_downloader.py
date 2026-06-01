import logging
import os
import re
import requests
from bs4 import BeautifulSoup


class HttpDownloader(object):
    url_prefix = "https://navteq.subscribenet.com/control/navt/"
    timeout = 30

    DOWNLOAD_STATUS_SUCCESS = 1
    DOWNLOAD_STATUS_SKIPPED = 0
    DOWNLOAD_STATUS_ERROR = -1

    def __init__(self):
        try:
            self.credential = {
                'username': os.environ['HERE_USERNAME'],
                'password': os.environ['HERE_PASSWORD'],
            }
        except KeyError as missing:
            raise RuntimeError(
                "Missing required environment variable {}. "
                "Set HERE_USERNAME and HERE_PASSWORD before running HttpDownloader.".format(missing)
            )
        self.session = None
        self.home_page = None
        self.product_name = ""
        self.product_page = None
        self.product_page_previous_releases = None
        self.release_page = None
        if 'https_proxy' in os.environ:
            del os.environ['https_proxy']
        if 'http_proxy' in os.environ:
            del os.environ['http_proxy']

    def download_data(self, product, release_name, version, local_dir):
        if product != self.product_name and not self.switch_to_product(product):
            return self.DOWNLOAD_STATUS_ERROR
        if not self.switch_to_release(release_name, version):
            return self.DOWNLOAD_STATUS_SKIPPED
        return self.download_from_release(local_dir)

    def data_exist(self, product, release_name, version):
        if product != self.product_name and not self.switch_to_product(product):
            return False
        return self.switch_to_release(release_name, version)

    def switch_to_product(self, product):
        if self.session:
            self.session.close()
        self.session = requests.Session()
        self.home_page = self.session.post(self.url_prefix + "home", data=self.credential,
                                           timeout=self.timeout)
        bs = BeautifulSoup(self.home_page.text, "lxml")
        product_item = bs.find("a", {"title": product})
        if product_item is None:
            logging.error("No available data for product {}".format(product))
            return False
        self.product_page = self.session.post(self.url_prefix + product_item["href"], data=self.credential,
                                              timeout=self.timeout)
        self.product_page_previous_releases = self.session.post(self.url_prefix + product_item["href"] + "&ver=ARC",
                                                                data=self.credential, timeout=self.timeout)
        self.product_name = product
        logging.info("Switch to product {}".format(product))
        return True

    def switch_to_release(self, release_name, version):
        if self.session:
            self.session.close()
        self.session = requests.Session()
        bs = BeautifulSoup(self.product_page.text, "lxml")
        product_list_table = bs.find("table", {"id": "epProductListTable"}).find_all("tbody")
        bs = BeautifulSoup(self.product_page_previous_releases.text, "lxml")
        product_list_table.extend(bs.find("table", {"id": "epProductListTable"}).find_all("tbody"))
        self.release_page = None
        for product in product_list_table:
            product_attr = product.tr.find_all("td")
            release_description = product_attr[1].a if product_attr[1].a else product_attr[2].a
            if product_attr[0].string == version and release_description.string.startswith(release_name):
                self.release_page = self.session.post(self.url_prefix + release_description["href"],
                                                      data=self.credential, timeout=self.timeout)
                logging.info("Switch to release {}".format(release_description.string))
                return True
        logging.error("No release match the version and name: {}, {}".format(version, release_name))
        return False

    def download_from_release(self, local_dir):
        if not os.path.isdir(local_dir):
            os.makedirs(local_dir)
        bs = BeautifulSoup(self.release_page.text, "lxml")
        for f in bs.findAll("tbody", {"class": "fileContainer collapsed"}):
            download_link = f.find("a", {"class": "download-link"})
            if not download_link:
                continue
            file_name = os.path.join(local_dir, download_link.string)
            file_link = download_link["href"]
            file_md5 = ""
            feat = f.find("table", {"class": "featList"})
            for tr in feat.findAll("tr"):
                if tr.find("th").string == "MD5 Signature":
                    file_md5 = tr.find("td").string
            if self.check_md5(file_name, file_md5):
                logging.info("File {} has already been downloaded, skip download".format(file_name))
                continue
            logging.info("Begin download file {}".format(file_name))
            os.system("wget -q \'{}\' -O \'{}\'".format(file_link, file_name))
            if self.check_md5(file_name, file_md5):
                logging.info("Download file {} succeeded!".format(file_name))
            else:
                logging.error("Download file {} failed! MD5 not match".format(file_name))
                return self.DOWNLOAD_STATUS_ERROR
        return self.DOWNLOAD_STATUS_SUCCESS

    def check_md5(self, file_name, file_md5):
        md5 = self.get_md5(file_name)
        return md5 == file_md5
    
    @staticmethod
    def get_md5(file_name):
        if os.path.isdir(file_name):
            output = os.popen("tar cf - \'{}\' | md5sum".format(file_name))
        else:
            output = os.popen("md5sum \'{}\'".format(file_name))
        md5_re = "([a-fA-F0-9]{32})"
        result = re.match(md5_re, output.read())
        return result.group(0) if result else "false"
