import os
import sys
from pathlib import Path
from random import choice
from shutil import copyfile
from shutil import copy2
from shutil import copytree
from random import choice
from datetime import datetime
from datetime import timezone
from inspect import cleandoc
import locale
import calendar
from time import gmtime
from distutils.dir_util import copy_tree
from filecmp import dircmp
from distutils import dir_util
from shutil import rmtree




def init():
    try:
        os.mkdir(os.getcwd() + "\\.wit")
        os.mkdir(os.getcwd() + "\\.wit\\images")
        os.mkdir(os.getcwd() + "\\.wit\\staging_area")
    except FileExistsError:
        pass


def get_wit_dir_and_rel_path(path):
    abspath = Path(os.path.abspath(path))
    flag = True
    while flag:
        prev = abspath
        possible_wit_dir = os.path.join(abspath, '.wit')
        abspath = Path(abspath.parent)
        if not abspath:
            flag = False
        if os.path.isdir(possible_wit_dir):
            return possible_wit_dir, os.path.relpath(prev.resolve(), start=abspath.resolve())
 

def add(path):
    isFile = os.path.isfile(path)
    isDirectory = os.path.isdir(path)
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    staging_area_path = wit_dir + '\\staging_area'
    if isFile:
        try:
            copy2(path, staging_area_path)
        except FileExistsError:
            pass

    elif isDirectory:
        try:
            if os.getcwd() == str(Path(wit_dir).parent):
                dest = staging_area_path + '\\' + path
                copytree(path, dest)
            else:
                dest = staging_area_path + '\\' + rel_path + '\\' + path
                copytree(path, dest)
        except FileExistsError:
            pass
    else:
        print("invalid path!")


def commit(message):
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    staging_area_path = wit_dir + '\\staging_area'
    references_path = wit_dir + '\\references.txt'
    choices = '1234567890abcdef'
    commit_id = ''.join(choice(choices) for i in range(40))
    commit_id_path = images_path + "\\" + commit_id
    os.mkdir(commit_id_path)
    create_commit_metadata(images_path, references_path, commit_id, message)
    copy_tree(staging_area_path, commit_id_path)
    try:
        head = get_from_references()
        master = get_from_references(False)
    except FileNotFoundError:
        master = commit_id  # first commit
        pass  # TODO log it
    else:
        if head == master:  
            master = commit_id  # otherwise master shouldn't change

    with open(references_path, 'w+') as f:
        f.write(f"HEAD={commit_id}\nmaster={master}\n")


def create_commit_metadata(images_path, references_path, commit_id, message):
    file_name = commit_id + '.txt'
    file_path = images_path + '\\' + file_name
    formatted_date = get_formatted_date()
    try:
        with open(references_path, 'r') as f:
            parent = f.readline().strip().split('=')[1]
    except FileNotFoundError:  # First commit
        # TODO log it
        parent = None

    metadata = f"""
    parent={parent}
    date={formatted_date}
    message={message}
    """
    try:
        with open(file_path, "w") as f:
            f.write(cleandoc(metadata))
    except IOError:
        raise


def get_formatted_date():
    date_components = []
    now = datetime.now()

    day = now.strftime("%d")
    date_components.append(calendar.day_abbr[int(day)])

    month = now.strftime("%m")
    date_components.append(calendar.month_abbr[int(month)])

    date_components.append(day)

    time = now.strftime("%H:%M:%S")
    date_components.append(time)

    year = now.strftime("%Y")
    date_components.append(year)

    """
    Credit for the next line:
    Source: https://forum.dynamobim.com/u/Dimitar_Venkov
    User: Dimitar_Venkov
    Profile: https://forum.dynamobim.com/u/dimitar_venkov/summary
    """
    offset = datetime.now() - datetime.utcnow()
    tz = '+' + str(int(offset.seconds / 3600)).zfill(2) + '00'
    date_components.append(tz)

    final_date = " ".join(date_components)
    return final_date


def get_from_references(HEAD=True):
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    references_path = wit_dir + '\\references.txt'
    if HEAD:
        line_idx = 0
    else:
        line_idx = 1
    try:
        with open(references_path, 'r') as f:
             return f.readlines()[line_idx].strip().split('=')[1]
    except FileNotFoundError:  # First commit
        # TODO log it
        return None


def status(get_info=False):
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    staging_area_path = wit_dir + '\\staging_area'
    head = get_from_references()
    if not head:
        return
    
    status_dict = {"to_be_committed": [], "not staged for commit": [], "untracked": []}
    head_path = images_path + '\\' + head
    dcmp_staging_and_head = dircmp(staging_area_path, head_path) 
    difference = get_changes_to_commit(dcmp_staging_and_head, staging_area_path, status_dict, 'to_be_committed')
    wit_dir_parent = Path(wit_dir).parent
    dcmp_staging_and_original = dircmp(staging_area_path, wit_dir_parent) 
    get_diff_files(dcmp_staging_and_original, status_dict, "not staged for commit")
    dcmp_original_and_staging = dircmp(wit_dir_parent, staging_area_path) 
    get_untracked_files(dcmp_original_and_staging, wit_dir_parent, status_dict, "untracked")
    status_message = "---Status---\n"
    status_message += f"\n-HEAD-\n{head}"
    status_message += "\n\n-Changes to be committed-\n"
    to_be_committed = status_dict["to_be_committed"]
    for item in to_be_committed:
        status_message += item + '\n'

    status_message += "\n\n-Changes not staged for commit-\n"
    not_staged_for_commit = status_dict["not staged for commit"]
    for item in not_staged_for_commit:
        status_message += item + '\n'

    status_message += "\n\n-Untracked files-\n"
    untracked = status_dict["untracked"]
    for item in untracked:
        status_message += item + '\n'

    if get_info:
        return status_dict
    print(cleandoc(status_message))    
    

"""
Credit for the following function
Source: https://docs.python.org/2/library/filecmp.html
"""
def get_diff_files(dcmp, status_dict, key):   
    for file_name in dcmp.diff_files:
        status_dict[key].append(os.path.abspath(file_name))
    for sub_dcmp in dcmp.subdirs.values():
        get_diff_files(sub_dcmp, status_dict, key)


def get_changes_to_commit(dcmp, path, status_dict, key):
    get_left_only(dcmp, path, status_dict, key)
    for file_name in dcmp.diff_files:
        status_dict[key].append(os.path.join(path, file_name))

    for sub_dcmp in dcmp.subdirs.values():
        get_changes_to_commit(sub_dcmp, sub_dcmp.left, status_dict, key)

def get_untracked_files(dcmp, path, status_dict, key):
    get_left_only(dcmp, path, status_dict, key)
    for sub_dcmp in dcmp.subdirs.values():
        get_untracked_files(sub_dcmp, sub_dcmp.left, status_dict, key)


def get_left_only(dcmp, path, status_dict, key):
    current_path = path
    for item in dcmp.left_only:
        if not item.endswith('.wit'):
            item_path = str(current_path) + '\\' + item
            is_directory = os.path.isdir(item_path)
            is_file = os.path.isfile(item_path)
            if is_file:
                status_dict[key].append(item_path)
            elif is_directory:
                current_path = item_path
                """
                Credit for the following code
                Source: https://stackoverflow.com/questions/2909975/python-list-directory-subdirectory-and-files
                User: https://stackoverflow.com/users/8206/eli-bendersky
                """
                for path, _, files in os.walk(current_path):
                    for file_name in files:
                        status_dict[key].append(os.path.join(path, file_name))

def checkout(commit_id):
    master = get_from_references(False)
    if commit_id == "master":
        commit_id = master
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    staging_area_path = wit_dir + '\\staging_area'
    references_path = wit_dir + '\\references.txt'
    head = get_from_references()
    head_path = images_path + '\\' + head
    wit_dir_parent = str(Path(wit_dir).parent)

    src = images_path + '\\' + commit_id 
    dst = wit_dir_parent
    status_dict = status(True)
    if status_dict["to_be_committed"] or status_dict["not staged for commit"]:
        return
    dir_util.copy_tree(src, dst)
    with open(references_path, 'w+') as f:
        f.write(f"HEAD={commit_id}\nmaster={master}\n")
        clean_dir(staging_area_path)
        dir_util.copy_tree(src, staging_area_path)


def clean_dir(delete_from):
    for f in os.listdir(delete_from):
        f_path = os.path.join(delete_from, f)
        if os.path.isdir(f_path):
            rmtree(f_path)
        elif os.path.isfile(f_path):
            os.remove(f_path)
        

if __name__ == "__main__":
    if len(sys.argv) == 2:

        if sys.argv[1] == "init":
            init()

        elif sys.argv[1] == "status":
            status()

    elif len(sys.argv) == 3:

        if sys.argv[1] == "add":
            add(sys.argv[2])

        elif sys.argv[1] == "commit":
            commit(sys.argv[2])

        elif sys.argv[1] == "checkout":
            checkout(sys.argv[2])