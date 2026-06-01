import os


def extract_kor_zip():
    extract_and_remove_zip_files()
    remove_sub_directory()


def extract_kor_speed_camera():
    extract_kor_zip()
    remove_sub_directory()


def extract_and_remove_zip_files():
    file_list = os.listdir()
    for f in file_list:
        if f.endswith(".zip"):
            os.system("unzip '{}';rm '{}'".format(f, f))


def remove_sub_directory():
    file_list = os.listdir()
    for f in file_list:
        if os.path.isdir(f):
            os.system("mv {}/* ./".format(f))
            os.rmdir(f)


def rename_kor_landmark_package():
    for f in os.listdir():
        if f.endswith(".zip"):
            os.system("mv {} KOR.zip".format(f))


def rename_kor_jv_package():
    for f in os.listdir():
        if f.endswith(".zip"):
            os.system("mv {} KOR_JV.zip".format(f))
