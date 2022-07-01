import csv
import json
from collections import defaultdict


def csv_to_python(filepath):
    f = open(filepath, 'r', encoding='utf-8')
    data = csv.reader(f)
    return data


def process_type_signature(value):
    if value == "Z":
        return "boolean"
    elif value == "B":
        return "byte"
    elif value == "C":
        return "char"
    elif value == "S":
        return "short"
    elif value == "I":
        return "int"
    elif value == "J":
        return "long"
    elif value == "F":
        return "float"
    elif value == "D":
        return "double"
    elif "L" in value:
        t = value[1:].replace("/", ".").replace("$", ".")
        if "java" in t:
            t = t.split(".")
            t = t[len(t) - 1]
        return t
    elif "[" in value:
        return "list"+process_type_signature(value[1:])
    else:
        return ""


def process_class(class_descriptor):
    if "$$" in class_descriptor:
        # pending
        return None
    elif "$" in class_descriptor:
        return class_descriptor[1:].replace("$", ".").replace("/", ".")
    else:
        return class_descriptor[1:].replace("/", ".")


def process_field(field):
    if ":" in field:
        i_field_name = field.split(":", 2)[0]
        i_field_type = process_type_signature(field.split(":", 2)[1])
        return i_field_name, i_field_type


def process_parameter(parameter):
    result = []
    if ";" in parameter:
        for par in parameter.split(";"):
            if process_type_signature(par) == "":
                for s in par:
                    result.append(process_type_signature(s))
            else:
                result.append(process_type_signature(par))
    return result


def process_method(method):
    if "(" in method:
        i_method_name = method.split("(")[0]
        if i_method_name == "<init>":
            i_method_name = "Constructor"
        elif i_method_name == "<clinit>":
            # pending
            return None
        i_parameter = process_parameter(method.split("(")[1].split(")")[0])
        i_return_type = process_type_signature(method.split("(")[1].split(")")[1])
        return i_method_name, i_parameter, i_return_type


if __name__ == '__main__':
    output = []
    entity = dict()
    for row in csv_to_python("E:\Android\hiddenapi-flags.csv"):
        for e in row:
            if e != "":
                if "->" in e:
                    if entity is not None:
                        output.append(entity)
                    entity = dict()
                    entity_name = ""
                    if process_class(e.split("->", 2)[0]) is None:
                        continue
                    class_qualified_name = process_class(e.split("->", 2)[0])
                    if "(" in e.split("->", 2)[1]:
                        if process_method(e.split("->", 2)[1]) is None:
                            continue
                        method_name, parameter, return_type = process_method(e.split("->", 2)[1])
                        if method_name == "Constructor":
                            temp = class_qualified_name.split(".")
                            method_name = temp[len(temp)-1]
                        entity_name = class_qualified_name+"."+method_name
                        entity["parameter"] = parameter
                        entity["rawType"] = return_type
                    else:
                        field_name, field_type = process_field(e.split("->", 2)[1])
                        entity_name = class_qualified_name + "." + field_name
                        entity["rawType"] = field_type.replace(";", "")
                    entity["entity_name"] = entity_name.replace(";", "")
                else:
                    if "hidden_api" in entity.keys():
                        entity["hidden_api"] = entity["hidden_api"]+" "+e
                    else:
                        entity["hidden_api"] = e
    with open("hiddenAPI.json", 'w') as f:
        json.dump(output, f, sort_keys=True, indent=4, separators=(',', ':'))
