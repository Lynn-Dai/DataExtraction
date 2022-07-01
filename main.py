# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import json
from collections import defaultdict


def json_to_python(filepath):
    f = open(filepath, 'r', encoding='utf-8')
    s = f.read()
    data = json.loads(s)
    return data


def process_und(data):
    count = 0
    cells = data['cells']
    data_dict = defaultdict(list)
    dest = ""
    for cell in cells:
        for detail in cell['details']:
            if detail.get('type') == 'Import':
                #     if '\\' in detail.get('dest').get('object'):
                #         dest = convert_path_to_object(detail.get('dest').get('object'))
                #     else:
                #         dest = detail.get('dest').get('object')
                #
                #     if dest in data_dict[unify_path(detail.get('src').get('object'))]:
                #         continue
                #     else:
                data_dict[unify_path(detail.get('src').get('object'))].append(detail.get('dest').get('object'))
                count = count + 1
    print(count)
    return data_dict


# def process_und(data):
#     count = 0
#     cells = data['cells']
#     data_dict = defaultdict(list)
#     dest = ""
#     for cell in cells:
#         for detail in cell['details']:
#             if detail.get('type') == 'Import':
#                     if '\\' in detail.get('dest').get('object'):
#                         dest = convert_path_to_object(detail.get('dest').get('object'))
#                     else:
#                         dest = detail.get('dest').get('object')
#
#                     if dest in data_dict[unify_path(detail.get('src').get('object'))]:
#                         continue
#                     else:
#                         data_dict[unify_path(detail.get('src').get('object'))].append(dest)
#                         count = count + 1
#     print(count)
#     return data_dict


def unify_path(path):
    if '\\' in path:
        components = path.split('\\')
        return '/'.join(components).split('halo-1.4.10/')[1]
    return path


def convert_path_to_object(path):
    if '\\' in path:
        components = path.split('\\')
        temp = '.'.join(components).split('java.')[1]
        return '.'.join(temp.split('.')[:-1])
    return path


def process_enre(data):
    cells = data['cells']
    data_dict = defaultdict(list)
    count = 0
    for cell in cells:
        for dest in cell['dest']:
            data_dict[cell['src']].append(dest)
            count = count + 1
    print(count)
    return data_dict


def verify_data_und(und, enre):
    data_dict = defaultdict(list)
    for src in und.keys():
        if src in enre.keys():
            for dest in und.get(src):
                if dest in enre.get(src):
                    pass
                else:
                    data_dict[src].append(dest)
        else:
            data_dict[src].append(und.get(src))
    return data_dict


def verify_data_enre(und, enre):
    data_dict = defaultdict(list)
    for src in enre.keys():
        if src in und.keys():
            for dest in enre.get(src):
                if dest in und.get(src):
                    pass
                else:
                    data_dict[src].append(dest)
        else:
            data_dict[src].append(und.get(src))
    return data_dict


def dict_to_json_write_file(data_dict, filename):
    with open(filename, 'w') as f:
        json.dump(data_dict, f, sort_keys=True, indent=4, separators=(',', ':'))


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    und = process_und(json_to_python('D:\pl_output\halo_1.txt'))
    enre = process_enre(json_to_python('D:\pl_output\halo-1.4.10-imports.json'))
    dict_to_json_write_file(verify_data_und(und, enre), 'und_have_but_enre_not.json')
    dict_to_json_write_file(verify_data_enre(und, enre), 'enre_have_but_und_not.json')
    # print(json.dumps(obj=verify_data_und(und, enre), indent=4))
