import calendar
from datetime import datetime
import os
import sys
from filecmp import dircmp
from distutils import dir_util
from inspect import cleandoc
from pathlib import Path
from random import choice
from shutil import copy2, copytree, rmtree

import matplotlib.pyplot as plt
import networkx as nx


class InvalidCommidIdError(Exception):
    def __init__(self, commit_id):
        self.commit_id = commit_id
    
    def __str__(self):
        return f"Invalid commit id: {self.commit_id}"


class InvalidPathError(Exception):
    def __init__(self, path):
        self.path = path

    def __str__(self):
        return f"Invalid path: {self.path}"


class InvalidCommandError(Exception):
    def __init__(self, arg1, arg2=None, arg3=None):
        self.arg1 = arg1
        self.arg2 = arg2
        self.arg3 = arg3

    def __str__(self):
        if self.arg3:
            return f"Invalid command: {self.arg1} {self.arg2} {self.arg3}"
        elif self.arg2:
            return f"Invalid command: {self.arg1} {self.arg2} {self.arg3}"
        else:
            return f"Invalid command: {self.arg1}"


class BranchExistsError(Exception):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"Branch {self.name} already exists"


def init():
    try:
        os.mkdir(os.getcwd() + "\\.wit")
        os.mkdir(os.getcwd() + "\\.wit\\images")
        os.mkdir(os.getcwd() + "\\.wit\\staging_area")
    except FileExistsError:
        pass

    activated_path = os.getcwd() + '\\.wit\\activated.txt'
    with open(activated_path, 'w') as f:
        f.write("master")


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
        raise InvalidPathError(path)


def replace_line_in_references(references_path, branch_name, commit_id):
    with open(references_path, 'r') as f:
        content = f.readlines()
        for i in range(len(content)):
            if content[i].split("=")[0] == branch_name:
                content[i] = f"{branch_name}={commit_id}\n"
                content = "".join(content)

    with open(references_path, 'w') as f:
        f.write(content)


def commit(message, merge=False, parents=None):
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    staging_area_path = wit_dir + '\\staging_area'
    references_path = wit_dir + '\\references.txt'
    activated_path = wit_dir + '\\activated.txt'
    references = get_references()

    choices = '1234567890abcdef'
    commit_id = ''.join(choice(choices) for i in range(40))
    commit_id_path = images_path + "\\" + commit_id
    os.mkdir(commit_id_path)
    create_commit_metadata(images_path, references_path, commit_id, message, merge, parents)
    dir_util.copy_tree(staging_area_path, commit_id_path)
    try:
        head = get_references()["HEAD"]
        master = get_references()["master"]

    except FileNotFoundError:
        master = commit_id  # first commit
        pass  # TODO log it

    # get activated
    with open(activated_path, 'r') as f:
        activated = f.read().strip()

    # replace master if needed
    if head == master and activated == "master": 
        replace_line_in_references(references_path, "master", master)

    # replace activated commit_id if needed
    if references[activated] == head or merge:
        replace_line_in_references(references_path, activated, commit_id)
    
    # replace HEAD
    replace_line_in_references(references_path, "HEAD", commit_id)
    print(f"Created new commit: {commit_id}")
   

def create_commit_metadata(images_path, references_path, commit_id, message, merge=False, parents=None):
    file_name = commit_id + '.txt'
    file_path = images_path + '\\' + file_name
    formatted_date = get_formatted_date()
    try:
        with open(references_path, 'r') as f:
            parent = f.readline().strip().split('=')
            if merge:
                parent = parents
            else:
                parent = parent[1]
    except FileNotFoundError:  # First commit
        # TODO log it
        parent = None

    if merge:
        metadata = f"""
        parent={parent[0]}, {parent[1]}
        date={formatted_date}
        message={message}
        """
    else:
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

    day = now.strftime("%a")
    date_components.append(day)

    month = now.strftime("%m")
    date_components.append(calendar.month_abbr[int(month)])

    day = now.strftime("%d")
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


def get_references():
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    references_path = wit_dir + '\\references.txt'
    try:
        with open(references_path, 'r') as f:
            lines = f.readlines()
            return {line.strip().split("=")[0]: line.strip().split("=")[1] for line in lines}
    except FileNotFoundError:  # First commit
        # TODO log it
        return None


def status(get_info=False):
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    staging_area_path = wit_dir + '\\staging_area'
    head = get_references()['HEAD']
    if not head:
        return
    
    status_dict = {"to_be_committed": [], "not staged for commit": [], "untracked": []}
    head_path = images_path + '\\' + head
    dcmp_staging_and_head = dircmp(staging_area_path, head_path) 
    get_changes_to_commit(dcmp_staging_and_head, staging_area_path, status_dict, 'to_be_committed')
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
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    images_list = os.listdir(images_path)
    staging_area_path = wit_dir + '\\staging_area'
    references_path = wit_dir + '\\references.txt'
    activated_path = wit_dir + '\\activated.txt'
    wit_dir_parent = str(Path(wit_dir).parent)

    branches = get_references()
    if commit_id in branches:
        activated = commit_id
        commit_id = branches[commit_id]
    elif commit_id not in images_list:
            raise InvalidCommidIdError(commit_id)
    else:
        activated = "None"

    with open(activated_path, 'w') as f:
        print(f"activated: {activated}")
        f.write(activated)
    
    src = images_path + '\\' + commit_id 
    dst = wit_dir_parent
    status_dict = status(True)
    if status_dict["to_be_committed"] or status_dict["not staged for commit"]:
        return
    dir_util.copy_tree(src, dst)
    replace_line_in_references(references_path, "HEAD", commit_id)

    clean_dir(staging_area_path)
    dir_util.copy_tree(src, staging_area_path)


def clean_dir(delete_from):
    for f in os.listdir(delete_from):
        f_path = os.path.join(delete_from, f)
        if os.path.isdir(f_path):
            rmtree(f_path)
        elif os.path.isfile(f_path):
            os.remove(f_path)


def graph():
    nodes, edges, merge = get_nodes_and_edges()
    g = nx.DiGraph()
    a = nodes[0]
    a = a[:20] + '\n' + a[20:]
    if len(nodes) > 1:
        b = nodes[1]
        b = b[:20] + '\n' + b[20:]
        nodes_to_display = [a, b]
        g.add_edge(a, b)
    if len(nodes) > 1 and merge:
        c = nodes[2]
        c = c[:20] + '\n' + c[20:]
        nodes_to_display.append(c)
        g.add_edge(a, c)
    else:
        nodes_to_display = [a]
    g.add_nodes_from(nodes_to_display)
    pos = nx.circular_layout(g, scale=0.1)
    options = {
        'node_color': 'blue',
        'font_color': 'red',
        'node_size': 10000,
        'width': 2,
        'arrowstyle': '->',
        'arrowsize': 25,
        'font_size': 7,
        'font_weight': 'bold',
    }
    nx.draw_networkx(g, pos, **options)
    plt.axis('off')
    plt.show()


def get_nodes_and_edges():
    nodes = []
    edges = []
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    head = get_references()["HEAD"]
    nodes.append(head)
    parent_path = images_path + '\\' + head + '.txt'
    parent = ""
    with open(parent_path, 'r') as f:
        parents = f.readline().strip().split('=')[1].split(', ')
        if len(parents) > 1:
            merge = True
            parent = parents[0]
            parent2 = parents[1]
            nodes.append(parent)
            nodes.append(parent2)
            edges.append((head, parent))
            edges.append((head, parent2))
        else:
            merge = False
            parent = parents[0]
            nodes.append(parent)
            edges.append((head, parent))
        parent_path = images_path + '\\' + parent + '.txt'
    return nodes, edges, merge


def branch(name):
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    references_path = wit_dir + '\\references.txt'
    references = get_references()
    head = references["HEAD"]
    with open(references_path, 'a+') as f:        
        if name not in references:
            f.write(f"{name}={head}\n")
        else:
            raise BranchExistsError(name)


def merge(branch_name):
    path = os.getcwd()
    wit_dir, rel_path = get_wit_dir_and_rel_path(path)
    images_path = wit_dir + '\\images'
    references = get_references()
    head_commit_id = references["HEAD"]
    branch_name_commit_id = references[branch_name]
  
    # find common_base for branch_name and head (by color idea)
    common_base_commit_id = get_common_base(images_path, head_commit_id, branch_name_commit_id)

    # find which files have changed between head and common_base,
    # as well as branch_name and common_base (compare two and two)
    status_dict = {"changes": []}
    head_path = images_path + '\\' + head_commit_id
    branch_name_path = images_path + '\\' + branch_name_commit_id
    common_base_path = images_path + '\\' + common_base_commit_id
    dcmp_head_and_base = dircmp(head_path, common_base_path)
    dcmp_branch_and_base = dircmp(branch_name_path, common_base_path)
   
    get_changes_to_commit(dcmp_head_and_base, head_path, status_dict, 'changes')
    get_changes_to_commit(dcmp_branch_and_base, branch_name_path, status_dict, 'changes')
    for item in status_dict['changes']:
        add(item)

    # create a new commit with two parents
    parents = [head_commit_id, branch_name_commit_id]
    commit(f"merged {head_commit_id} and {branch_name_commit_id}", True, parents)


def get_common_base(images_path, commit1, commit2):
    seen = []

    # find the ancestors of commit1
    current = commit1
    while current != "None":
        seen.append(current)
        current = get_parent(images_path, current)[0].strip()

    # get the base
    found_base = False
    current = commit2
    while current != "None" and not found_base:
        if current in seen:
            found_base = True
            base = current
        current = get_parent(images_path, current)[0].strip()

    return base
    

def get_parent(images_path, current):
    file_path = images_path + '\\' + current + '.txt'
    parent = ""
    with open(file_path, 'r') as f:
        parent = f.readline().split("=")[1]
        parent = parent.split(", ")
        return parent


if __name__ == "__main__":
    if len(sys.argv) == 2:

        if sys.argv[1] == "init":
            init()

        elif sys.argv[1] == "status":
            status()

        elif sys.argv[1] == "graph":
            graph()

        else:
            raise InvalidCommandError(sys.argv[0], sys.argv[1])

    elif len(sys.argv) == 3:

        if sys.argv[1] == "add":
            add(sys.argv[2])

        elif sys.argv[1] == "commit":
            commit(sys.argv[2])

        elif sys.argv[1] == "checkout":
            checkout(sys.argv[2])

        elif sys.argv[1] == "branch":
            branch(sys.argv[2])

        elif sys.argv[1] == "merge":
            merge(sys.argv[2])

        else:
            raise InvalidCommandError(sys.argv[0], sys.argv[1], sys.argv[2])
    else:
        raise InvalidCommandError(sys.argv[0])