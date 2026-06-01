import os
import time


def extract_landmark(doc_dir):
    extract_and_remove_tar_files()
    os.system("mv *.pdf {}/;mv *.csv {}/;mv *.xlsx {}/".format(doc_dir, doc_dir, doc_dir))


def extract_speed_camera(doc_dir):
    extract_and_remove_tar_files()
    os.system("mv *.pdf {}/".format(doc_dir))
    os.system("rm -rf DOCUMENTATION;rm -rf DEFINITIONS;rm -rf XSD;rm Release*")


def extract_speed_pattern(doc_dir):
    extract_and_remove_tar_files()
    os.system("mv *.pdf {}/".format(doc_dir))
    extract_and_remove_zip_files()
    os.system("mv *.csv {}/".format(doc_dir))
    file_list = os.listdir()
    for file in file_list:
        if os.path.isdir(file):
            os.system("mv {}/*.zip ./".format(file))
            os.system("rm -rf {}".format(file))
    os.system("for zipfile in *.zip; do 7za x $zipfile;rm $zipfile; done")
    file_list = os.listdir()
    for file in file_list:
        if os.path.isdir(file):
            os.system("mv {}/*.csv ./".format(file))
            os.system("rm -rf {}".format(file))
    os.system("gzip *.csv")


def extract_junction(doc_dir):
    file_list = os.listdir()
    for f in file_list:
        if f.endswith(".tar"):
            os.system("tar -xvf {} *stats.csv;tar -xvf {} *.pdf".format(f, f))
            os.system("mv *.pdf {}/;mv *.csv {}/".format(doc_dir, doc_dir))


def extract_gjv(doc_dir):
    extract_junction(doc_dir)
    gjv_dir = "../../GJV"
    os.makedirs(gjv_dir, exist_ok=True)
    file_list = os.listdir()
    for f in file_list:
        if f.endswith(".tar"):
            os.system("tar -xvf {} *_LAT.csv".format(f))
            os.system("mv *.csv {}".format(gjv_dir))


def extract_postal_code(doc_dir):
    extract_and_remove_tar_files()
    file_list = os.listdir()
    for f in file_list:
        if f.endswith(".zip"):
            os.system("unzip '{}';rm '{}'".format(f, f))
            os.system("chmod -R 775 txt;chmod -R 775 shp")
    os.system("mv *.pdf {}/;mv DIFF* {}/;mv *.xls {}/".format(doc_dir, doc_dir, doc_dir))
    os.system("mv txt/* ./;rm -rf shp;rm -rf txt")
    for txt_file in os.listdir():
        file_parts = txt_file.split('_')
        file_parts[0] = file_parts[0][0:2]
        del file_parts[1]
        new_file = '_'.join(file_parts)
        os.system("mv {} {}".format(txt_file, new_file))


def extract_postal_address(doc_dir):
    extract_and_remove_tar_files()
    extract_and_remove_zip_files()
    os.system("mv *.pdf {}".format(doc_dir))


def package_eu_traffic_location(doc_dir):
    folder_list = os.listdir()
    quarter = doc_dir.split(os.path.sep)[6].split('_')[-1]
    os.system("rm -rf TrafficLocation_{}_*".format(quarter))
    package_name = "TrafficLocation_{}_{}".format(quarter, time.strftime("%Y%m%d", time.localtime()))
    os.mkdir(package_name)

    # Extract TrafficNav data
    for folder in folder_list:
        if os.path.isdir(folder):
            os.chdir(folder)
            extract_and_remove_tar_files()
            os.system("mv *.pdf {}".format(doc_dir))
            os.chdir("../")
            os.system("mv {} {}/".format(folder, package_name))

    # Extract HERE Europe data
    os.system("mv *.tar {}/".format(package_name))
    os.chdir(package_name)
    extract_and_remove_tar_files()
    os.system("mv *.pdf {}".format(doc_dir))

    # Copy 3rd party data
    misc_location = "/var/www/html/data/MISC/EU_Location/{}".format(quarter)
    os.system("cp -r {}/* ./".format(misc_location))

    # Manually replace NAMES.dat file for Slovakia
    if os.path.isdir("Slovakia"):
        os.chdir("Slovakia")
        solvakia_zip_file = [f for f in os.listdir() if ".zip" in f][0]
        os.system("unzip {}".format(solvakia_zip_file))
        os.system("mv ../Slovakia_Names/NAMES.dat ./")
        os.system("zip -m {} *.dat".format(solvakia_zip_file))
        os.chdir("../")
        os.system("rm -rf Slovakia_Names")

    os.system("tar -cvf ../{}.tar *".format(package_name))


def extract_and_remove_tar_files():
    file_list = os.listdir()
    for f in file_list:
        if f.endswith(".tar"):
            os.system("tar -xvf '{}';rm '{}'".format(f, f))


def extract_and_remove_zip_files():
    file_list = os.listdir()
    for f in file_list:
        if f.endswith(".zip"):
            os.system("unzip '{}';rm '{}'".format(f, f))

