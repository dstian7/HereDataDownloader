import os
import json
import time
import datetime
import xlrd

import tn_toll_cost_validator
from version_config_generator import *
from tn_toll_cost_validator import TnTollCostValidator


class DataChecker:
    def __init__(self, region, version, main_data_path):
        self.region = region
        self.version = version
        self.main_data_path = main_data_path
        self.history_file_name = os.path.join(self.main_data_path, ".download_history")
        self.report_path = os.path.join(self.main_data_path, "check_report")
        os.makedirs(self.report_path, exist_ok=True)
        self.main_result_info = self.load_main_result_info()

    CHECK_STATUS_PASS = "pass"
    CHECK_STATUS_WARNING = "warning"
    CHECK_STATUS_ERROR = "error"
    CHECK_STATUS_NOT_READY = "not ready"
    MAIN_RESULT_JSON_FILE = "main_result.json"

    def load_main_result_info(self):
        result_file_name = os.path.join(self.report_path, self.MAIN_RESULT_JSON_FILE)
        if not os.path.isfile(result_file_name):
            return {"region": self.region, "version": self.version, "cygnus_components": {}}
        with open(result_file_name) as f:
            return json.load(f)

    def is_component_downloaded(self, component, cygnus_component):
        if cygnus_component not in self.main_result_info["cygnus_components"]:
            return False
        for item in self.main_result_info["cygnus_components"][cygnus_component]:
            if component["name"] == item["name"] and item["status"] in [self.CHECK_STATUS_PASS, self.CHECK_STATUS_WARNING]:
                logging.info("Component {} has already been downloaded, skip download".format(component["name"]))
                return True
        return False

    def check_component(self, component, cygnus_component, download_version=""):
        if "check_method" not in component:
            return False
        if cygnus_component not in self.main_result_info["cygnus_components"]:
            self.main_result_info["cygnus_components"][cygnus_component] = []
        else:
            self.main_result_info["cygnus_components"][cygnus_component] = [
                x for x in self.main_result_info["cygnus_components"][cygnus_component]
                if component["name"] != x["name"]]
        logging.info("Check {} data".format(component["name"]))

        if download_version:
            component["download_version"] = download_version
        update_time = self.get_update_time(component["name"])
        check_method = getattr(DataChecker, component["check_method"])
        main_result, sub_result = check_method(self, component)
        if update_time or main_result["status"] not in [self.CHECK_STATUS_ERROR, self.CHECK_STATUS_NOT_READY]:
            main_result["update_time"] = update_time
            if not main_result.get("detail_link"):
                main_result["detail_link"] = "detail_report.html?component={}".format(component["name"])
            self.write_component_json_file(component["name"], sub_result)
        else:
            main_result = {"status": self.CHECK_STATUS_NOT_READY}
        if self.region not in ["KOR", "PAK"]:
            main_result["here_schedule"] = self.get_here_schedule(component["name"], download_version)
        main_result["name"] = component["name"]
        if download_version:
            here_version = get_file_version(download_version,
                                            component.get("standalone_version", "") == "True")
            main_result["version"] = download_version
            main_result["here_version"] = here_version
        self.main_result_info["cygnus_components"][cygnus_component].append(main_result)
        return main_result.get("status", self.CHECK_STATUS_NOT_READY) in [self.CHECK_STATUS_PASS,
                                                                          self.CHECK_STATUS_WARNING]

    def get_update_time(self, component_name):
        if not os.path.isfile(self.history_file_name):
            return ""
        with open(self.history_file_name) as history_file:
            lines = history_file.readlines()
            for line in reversed(lines):
                line_parts = line.split('|')
                if len(line_parts) < 2:
                    continue
                if component_name == line_parts[0]:
                    return line_parts[2].rstrip()
        return ""

    def check_file_fixed_name(self, component):
        return self.check_file_one_by_one(component, self.get_existing_file, self.get_file_size)

    def check_file_with_version(self, component):
        return self.check_file_one_by_one(component, self.get_existing_file_with_version, self.get_file_size)

    def check_by_folder(self, component):
        return self.check_file_one_by_one(component, self.get_existing_folder, self.get_folder_size)

    def check_file_one_by_one(self, component, check_file_exist_func, get_file_size_func):
        ref_files = component["ref_files"]
        main_check_result = {"ref_count": len(ref_files)}
        sub_check_result = {"component": component["name"], "details": []}
        version = self.version
        if "download_version" in component:
            version = component["download_version"]
        prev_version = get_previous_version(version)
        current_version = get_file_version(version, component.get("standalone_version"))
        previous_version = get_file_version(prev_version, component.get("standalone_version"))
        current_data_path = str(os.path.join(self.main_data_path, component["local_dir"]))
        base_data_path = current_data_path.replace(self.version, prev_version)
        pass_count = warning_count = error_count = 0
        total_size = ref_total_size = 0
        existing_files = os.listdir(current_data_path) if os.path.isdir(current_data_path) else []

        for ref in ref_files:
            sub_result_detail = {"file_name": "", "file_size": "", "ref_file_name": ref, "ref_file_size": "",
                                 "status": "", "message": ""}
            current_ref = ref.format(v=current_version)
            existing_file = check_file_exist_func(current_ref, current_data_path)
            if existing_file:
                sub_result_detail["file_name"] = existing_file
                sub_result_detail["file_size"] = get_file_size_func(os.path.join(current_data_path, existing_file))
                total_size += sub_result_detail["file_size"]
                existing_files = [f for f in existing_files if f != existing_file]
            else:
                sub_result_detail["file_name"] = current_ref.replace(r"\d", "0")
                sub_result_detail["status"] = self.CHECK_STATUS_ERROR
                sub_result_detail["message"] = "file missing"
                error_count += 1
                sub_check_result["details"].append(sub_result_detail)
                continue

            base_ref = ref.format(v=previous_version)
            existing_file = check_file_exist_func(base_ref, base_data_path)
            if existing_file:
                sub_result_detail["ref_file_name"] = existing_file
                sub_result_detail["ref_file_size"] = get_file_size_func(os.path.join(base_data_path, existing_file))
                ref_total_size += sub_result_detail["ref_file_size"]
                if self.abnormal_size_change(sub_result_detail["file_size"], sub_result_detail["ref_file_size"]):
                    sub_result_detail["status"] = self.CHECK_STATUS_WARNING
                    sub_result_detail["message"] = "Abnormal data size change"
                    warning_count += 1
                else:
                    sub_result_detail["status"] = self.CHECK_STATUS_PASS
                    pass_count += 1
            else:
                sub_result_detail["status"] = self.CHECK_STATUS_WARNING
                sub_result_detail["message"] = "ref file missing"
                warning_count += 1
            sub_check_result["details"].append(sub_result_detail)

        '''
        if existing_files:
            for existing_file in existing_files:
                sub_result_detail = {"file_name": existing_file, "file_size": "",
                                     "ref_file_name": "", "ref_file_size": "", "status": self.CHECK_STATUS_WARNING,
                                     "message": "unexpected file"}
                warning_count += 1
                sub_check_result["details"].append(sub_result_detail)
        '''

        total_result = {"file_name": "Total", "file_size": total_size, "ref_file_name": "Total",
                        "ref_file_size": ref_total_size, "status": "", "message": ""}
        sub_check_result["details"].append(total_result)

        main_check_result = self.update_main_result_count(main_check_result, pass_count, warning_count, error_count)
        return main_check_result, sub_check_result

    @staticmethod
    def get_existing_file(file_name, folder):
        return file_name if os.path.isfile(os.path.join(folder, file_name)) else None

    @staticmethod
    def get_existing_file_with_version(file_name, folder):
        if not os.path.isdir(folder):
            return None
        for data in os.listdir(folder):
            if re.match(file_name, data):
                return data
        return None

    @staticmethod
    def get_existing_folder(file_name, folder):
        return file_name if os.path.isdir(os.path.join(folder, file_name)) else None

    @staticmethod
    def get_file_size(file):
        return os.stat(file).st_size

    @staticmethod
    def get_folder_size(folder):
        return sum(os.stat(os.path.join(folder, f)).st_size for f in os.listdir(folder) if
                   os.path.isfile(os.path.join(folder, f)))

    def check_eu_traffic_location(self, component):
        ref_files = component["ref_files"]
        main_check_result = {"detail_link": "eu_traffic_location_report.html"}
        sub_check_result = {"component": component["name"], "details": []}
        current_data_path = str(os.path.join(self.main_data_path, component["local_dir"]))
        pass_count = warning_count = error_count = 0

        if os.path.isdir(current_data_path):
            for traffic_folder in os.listdir(current_data_path):
                if os.path.isdir(os.path.join(current_data_path,
                                              traffic_folder)) and traffic_folder.startswith("TrafficLocation_"):
                    current_data_path = os.path.join(current_data_path, traffic_folder)
                    break

        for ref in ref_files:
            sub_result_detail = {"folder": ref, "file_name": "", "table_version": "", "status": "", "message": ""}
            if not os.path.isdir(os.path.join(current_data_path, ref)):
                sub_result_detail["status"] = self.CHECK_STATUS_ERROR
                sub_result_detail["message"] = "file missing"
                error_count += 1
                sub_check_result["details"].append(sub_result_detail)
                continue
            zip_files = [x for x in os.listdir(os.path.join(current_data_path, ref)) if x.endswith(".zip")]
            if not zip_files:
                sub_result_detail["status"] = self.CHECK_STATUS_ERROR
                sub_result_detail["message"] = "file missing"
                error_count += 1
                sub_check_result["details"].append(sub_result_detail)
                continue
            sub_result_detail["file_name"] = "<br>".join(zip_files)
            table_versions = []
            for zip_file in zip_files:
                table_versions.append(self.get_location_table_version_from_zip(os.path.join(
                    current_data_path, ref, zip_file)))
            sub_result_detail["table_version"] = "<br>".join(table_versions)
            if sub_result_detail["table_version"]:
                sub_result_detail["status"] = self.CHECK_STATUS_PASS
                pass_count += 1
            else:
                sub_result_detail["status"] = self.CHECK_STATUS_WARNING
                sub_result_detail["message"] = "Can't get location table version"
                warning_count += 1
            sub_check_result["details"].append(sub_result_detail)

        main_check_result = self.update_main_result_count(main_check_result, pass_count, warning_count, error_count)
        return main_check_result, sub_check_result

    @staticmethod
    def get_location_table_version_from_zip(zip_file):
        try:
            version_file = os.popen("unzip -Z1 '{}' | grep LOCATIONDATASETS".format(zip_file)).readline().rstrip()
            os.system("unzip -p '{}' '{}' > version.txt".format(zip_file, version_file))
            version_line = os.popen("cat version.txt").readlines()[1]
            os.system("rm version.txt")
            return version_line.split(";")[3]
        except:
            return ""

    def check_tn_toll_cost(self, component):
        validator = TnTollCostValidator(self.region, self.version,
                                        str(os.path.join(self.main_data_path, component["local_dir"])))
        return validator.validate()

    @staticmethod
    def abnormal_size_change(data_size, ref_size):
        return int(data_size) < int(ref_size) * 0.8

    def update_main_result_count(self, main_check_result, pass_count, warning_count, error_count):
        main_check_result["pass"] = pass_count
        main_check_result["warning"] = warning_count
        main_check_result["error"] = error_count
        if error_count > 0:
            main_check_result["status"] = self.CHECK_STATUS_ERROR
        elif warning_count > 0:
            main_check_result["status"] = self.CHECK_STATUS_WARNING
        else:
            main_check_result["status"] = self.CHECK_STATUS_PASS
        return main_check_result

    def write_component_json_file(self, component_name, result):
        result_file_name = os.path.join(self.report_path, "{}.json".format(component_name))
        with open(result_file_name, "w") as result_file:
            result_file.write(json.dumps(result, indent=4))

    def generate_main_report(self):
        self.copy_report_html_file()
        main_result_file_name = os.path.join(self.report_path, self.MAIN_RESULT_JSON_FILE)
        self.main_result_info["time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with open(main_result_file_name, "w") as result_file:
            result_file.write(json.dumps(self.main_result_info, indent=4))

    def copy_report_html_file(self):
        template_path = os.path.join(str(os.path.dirname(__file__)), "check_template")
        os.system("cp {}/result_report.html {}/".format(template_path, self.report_path))
        os.system("cp {}/detail_report.html {}/".format(template_path, self.report_path))
        if self.region == "EU":
            os.system("cp {}/eu_traffic_location_report.html {}/".format(template_path, self.report_path))
        os.system("cp -r {}/javascript {}/".format(template_path, self.report_path))

    def get_here_schedule(self, component, version):
        file_version = get_file_version(version)
        region_dict = {"ANZ": ["AU/NZ"], "EU": ["EEU", "WEU", "EUROPE"], "MEA": ["MEA"], "NA": ["NA"],
                       "SA": ["SA"], "SEA": ["APAC", "Asia Pacific"], "TWN": ["TAIWAN"], "ISC": ["INDIA"],
                       "HKM": ["HONG KONG", "MACAU", "APAC"]}
        component_dict = {"rdf": [".*Core - DDF, RDF"], "rdf_hkg": [".*Core - DDF, RDF"],
                          "rdf_mac": [".*Core - DDF, RDF"], "gjv": ["2D Generalized Junctions.*"],
                          "landmark": ["3D Landmarks.*"], "speed_camera": ["Safety Cameras Transition.*"],
                          "speed_pattern": ["Traffic Patterns LINK.*"],
                          "2d_generalized_junctions": ["2D Generalized Junctions.*"],
                          "2d_generalized_signs": ["2D Generalized Signs.*"],
                          "2d_junctions": ["2D Junctions.*"],
                          "2d_signs": ["2D Signs.*"],
                          "traffic_location": ["Traffic Location Tables.*"],
                          "postal_code": ["Postal Code Points.*"], "postal_address": ["Postal Addressing.*"],
                          "environmental_zones": ["Environmental Zones.*"],
                          "toll_cost": ["Toll Costs.*"],
                          "commercial_vehicle_regulations": ["HERE Commercial Vehicle Regulations.*"],
                          "vehicle_regulations": ["HERE Vehicle Regulations.*"]
                          }
        if self.region not in region_dict:
            return ""
        region_index = region_dict[self.region]
        component_index = component_dict[component]
        excel_dir = "/var/www/html/docs/HERE/Product_Availability_Dates"
        files = os.listdir(excel_dir)
        max_score = 0
        latest_file = ""
        date = datetime.datetime(2000, 1, 1)
        final_date = datetime.datetime(2000, 1, 1)
        for file_name in files:
            m = re.match(r"^Q([1-4])'(\d+)", file_name)
            if m:
                quarter = int(m.group(1))
                year = int(m.group(2))
                score = year * 10 + quarter
                if score > max_score:
                    max_score = score
                    latest_file = file_name
        if "" == latest_file:
            return ""
        date_index = 0  # initialize
        with xlrd.open_workbook(os.path.join(excel_dir, latest_file)) as workbook:
            sheet = workbook.sheet_by_name("PRODUCT AVAILABILITY DATES")
            for i in range(0, len(sheet.row_values(1))):
                if file_version in str(sheet.row_values(1)[i]):
                    date_index = i
                    break
            for row in sheet.get_rows():
                final_date = self.__process_row(row, region_index, component_index, final_date, date, date_index,
                                                workbook)
        return final_date.strftime("%Y-%m-%d") if final_date != datetime.datetime(2000, 1, 1) else ""

    @staticmethod
    def __process_row(row, region_index, component_index, final_date, date, date_index, workbook):
        if row[1].value not in region_index:
            return final_date
        for component in component_index:
            if not re.match(component, row[4].value):
                continue
            if row[date_index].ctype == xlrd.sheet.XL_CELL_DATE:
                date = xlrd.xldate.xldate_as_datetime(row[date_index].value, workbook.datemode)
            if date > final_date:
                final_date = date
        return final_date

    @classmethod
    def component_ready(cls, component, data_path):
        main_result_json_file = os.path.join(data_path, "check_report", cls.MAIN_RESULT_JSON_FILE)
        if not os.path.isfile(main_result_json_file):
            return False
        with open(main_result_json_file) as f:
            main_result_info = json.load(f)
        for cygnus_component in main_result_info["cygnus_components"]:
            for item in main_result_info["cygnus_components"][cygnus_component]:
                if component["name"] == item["name"]:
                    return item["status"] in [cls.CHECK_STATUS_PASS, cls.CHECK_STATUS_WARNING]
        return False
