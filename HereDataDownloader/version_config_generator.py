import re
import sys
import logging

QUARTER_NUMBER_CHAR_DICT = {1: "E", 2: "F", 3: "G", 4: "H"}
STANDALONE_QUARTER_NUMBER_CHAR_DICT = {1: "P", 2: "Q", 3: "R", 4: "S"}
MAP_VERSION_TEMPLATE = "S{year}1R{quarter_num}"
ADD_VERSION_TEMPLATE = "S{year}1"
ADD_FULL_VERSION_TEMPLATE = "S{year}1_{quarter_char}"
FILE_VERSION_TEMPLATE = "{year}1{quarter_char}0"
MONTHLY_VERSION_TEMPLATE = "S{year}1_{month_num}"
MONTHLY_FILE_VERSION_TEMPLATE="{year}1{month_num}"

MONTHLY_VERSION_CONFIG = {
    "M01W1": {"here_version_number": "44", "base_quarter": "Q4", "jv_base_quarter": "Q4",
              "year_change": -1, "quarter_year_change": -1, "jv_year_change": -1},
    "M02W1": {"here_version_number": "48", "base_quarter": "Q1", "jv_base_quarter": "Q4",
              "year_change": -1, "jv_year_change": -1},
    "M03W1": {"here_version_number": "E0", "standalone_version_number": "P0", "base_quarter": "Q1",
              "jv_base_quarter": "Q1", "rdf_quarter": "Q2"},
    "M04W1": {"here_version_number": "05", "base_quarter": "Q1", "jv_base_quarter": "Q1"},
    "M05W1": {"here_version_number": "09", "base_quarter": "Q2", "jv_base_quarter": "Q1"},
    "M06W1": {"here_version_number": "F0", "standalone_version_number": "Q0", "base_quarter": "Q2",
              "jv_base_quarter": "Q2", "rdf_quarter": "Q3"},
    "M07W1": {"here_version_number": "18", "base_quarter": "Q2", "jv_base_quarter": "Q2"},
    "M08W1": {"here_version_number": "22", "base_quarter": "Q3", "jv_base_quarter": "Q2"},
    "M09W1": {"here_version_number": "G0", "standalone_version_number": "R0", "base_quarter": "Q3",
              "jv_base_quarter": "Q3", "rdf_quarter": "Q4"},
    "M10W1": {"here_version_number": "31", "base_quarter": "Q3", "jv_base_quarter": "Q3"},
    "M11W1": {"here_version_number": "35", "base_quarter": "Q4", "jv_base_quarter": "Q3"},
    "M12W1": {"here_version_number": "H0", "standalone_version_number": "S0", "base_quarter": "Q4",
              "jv_base_quarter": "Q4", "rdf_quarter": "Q1", "rdf_year_change": 1}
}


def parse_data_quarter(data_quarter):
    """Data quarter --> year,quarter_num . 17Q4 --> 17,4"""
    p = r"(\d\d)Q([1-4])"
    m = re.match(p, data_quarter)
    if not m:
        sys.stderr.write("Data quarter parser failed. [{}] is not format like 17Q4.\n".format(data_quarter))
        sys.exit(-1)
    return int(m.group(1)), int(m.group(2))


def get_last_quarter_split(quarter):
    """The last quarter. 17Q2 --> 17Q1, 17Q1--> 16Q4"""
    year, quarter_num = get_quarter_split(quarter)
    quarter_num = quarter_num - 1
    if quarter_num == 0:
        quarter_num = 4
        year = year - 1
    return year, quarter_num


def get_quarter_split(quarter):
    p = r"(\d\d)Q([1-4])"
    m = re.match(p, quarter)
    if not m:
        logging.error("Invalid data quarter {}".format(quarter))
        sys.exit(-1)
    year = int(m.group(1))
    quarter_num = int(m.group(2))
    return year, quarter_num


def get_monthly_split(month):
    p = r"(\d\d)[Mm](0[1-9]|1[0-2])"
    m = re.match(p, month)
    if not m:
        logging.error("Invalid data month {}".format(month))
        sys.exit(-1)
    return m.group(1), m.group(2)


def get_previous_version(version):
    if is_quarter(version):
        year, quarter_num = get_last_quarter_split(version)
        return "{}Q{}".format(year, quarter_num)
    elif is_month(version):
        year, month_num = get_monthly_split(version)
        year = int(year)
        if month_num == "01":
            year -= 1
            month_num = "12"
        else:
            month_num = str(int(month_num) - 1).zfill(2)
        return "{}M{}W1".format(year, month_num)
    else:
        return None


def get_version(version, is_standalone=False):
    if is_quarter(version):
        return get_quarterly_version(version, is_standalone)
    elif is_month(version):
        return get_monthly_version(version)
    else:
        return None


def get_quarterly_version(data_quarter, is_standalone=False):
    map_year, map_quarter_num = get_last_quarter_split(data_quarter)
    quarter_char = STANDALONE_QUARTER_NUMBER_CHAR_DICT.get(map_quarter_num) if is_standalone else \
        QUARTER_NUMBER_CHAR_DICT.get(map_quarter_num)
    map_version = MAP_VERSION_TEMPLATE.format(year=map_year, quarter_num=map_quarter_num)
    add_version = ADD_VERSION_TEMPLATE.format(year=map_year)
    add_full_version = ADD_FULL_VERSION_TEMPLATE.format(year=map_year, quarter_char=quarter_char)
    return map_version, add_version, add_full_version


def get_monthly_version(version):
    map_year = int(version[0:2])
    monthly_version = version[2:]
    if monthly_version not in MONTHLY_VERSION_CONFIG:
        logging.error("Invalid version {}".format(version))
        return ""
    version_config = MONTHLY_VERSION_CONFIG.get(monthly_version)
    here_month_num = version_config.get("here_version_number")
    if "year_change" in version_config:
        map_year += version_config["year_change"]
    add_version = ADD_VERSION_TEMPLATE.format(year=map_year)
    full_version = MONTHLY_VERSION_TEMPLATE.format(year=map_year, month_num=here_month_num)
    return add_version, full_version


def get_file_version(data_version, is_standalone=False):
    if is_month(data_version):
        return get_monthly_file_version(data_version, is_standalone)
    elif is_standalone:
        return get_standalone_file_version(data_version)
    else:
        return get_normal_file_version(data_version)


def get_normal_file_version(data_version):
    map_year, map_quarter_num = get_last_quarter_split(data_version)
    quarter_char = QUARTER_NUMBER_CHAR_DICT.get(map_quarter_num)
    return FILE_VERSION_TEMPLATE.format(year=map_year, quarter_char=quarter_char)


def get_standalone_file_version(data_version):
    map_year, map_quarter_num = get_last_quarter_split(data_version)
    quarter_char = STANDALONE_QUARTER_NUMBER_CHAR_DICT.get(map_quarter_num)
    return FILE_VERSION_TEMPLATE.format(year=map_year, quarter_char=quarter_char)


def get_monthly_file_version(data_version, is_standalone=False):
    map_year = int(data_version[0:2])
    monthly_version = data_version[2:]
    if monthly_version not in MONTHLY_VERSION_CONFIG:
        logging.error("Invalid version {}".format(data_version))
        return ""
    version_config = MONTHLY_VERSION_CONFIG.get(monthly_version)
    here_month_num = version_config.get("here_version_number")
    if is_standalone:
        standalone_num = version_config.get("standalone_version_number", "")
        if standalone_num:
            here_month_num = standalone_num
    if "year_change" in version_config:
        map_year += version_config["year_change"]
    return MONTHLY_FILE_VERSION_TEMPLATE.format(year=map_year, month_num=here_month_num)


def is_month(version):
    return re.fullmatch(r'^\d{2}[Mm](0[1-9]|1[0-2])[Ww]\d$', version)


def is_quarter(version):
    return re.fullmatch(r'^\d{2}[Qq][1-4]$', version)


def get_base_quarter(version):
    year = int(version[0:2])
    monthly_version = version[2:]
    if monthly_version not in MONTHLY_VERSION_CONFIG:
        logging.error("Invalid version {}".format(version))
        return ""
    version_config = MONTHLY_VERSION_CONFIG.get(monthly_version)
    if "quarter_year_change" in version_config:
        year += version_config["quarter_year_change"]
    return "{}{}".format(year, version_config.get("base_quarter"))


def get_rdf_quarter(version):
    if is_month(version):
        year = int(version[0:2])
        monthly_version = version[2:]
        if monthly_version not in MONTHLY_VERSION_CONFIG:
            logging.error("Invalid version {}".format(version))
            return ""
        version_config = MONTHLY_VERSION_CONFIG.get(monthly_version)
        if "rdf_quarter" in version_config:
            if "rdf_year_change" in version_config:
                year += version_config["rdf_year_change"]
            return "{}{}".format(year, version_config.get("rdf_quarter"))
        else:
            return ""
    else:
        logging.error("Invalid version {}".format(version))
        return ""


def get_jv_quarter(version):
    if is_month(version):
        year = int(version[0:2])
        monthly_version = version[2:]
        if monthly_version not in MONTHLY_VERSION_CONFIG:
            logging.error("Invalid version {}".format(version))
            return ""
        version_config = MONTHLY_VERSION_CONFIG.get(monthly_version)
        if "jv_base_quarter" in version_config:
            if "jv_year_change" in version_config:
                year += version_config["jv_year_change"]
            return "{}{}".format(year, version_config.get("jv_base_quarter"))
        else:
            return ""
    else:
        logging.error("Invalid version {}".format(version))
        return ""


if __name__ == '__main__': # pragma: no cover
    version = "26M02W1"
    print(get_base_quarter(version))
    print(get_jv_quarter(version))
    print(get_previous_version(version))
