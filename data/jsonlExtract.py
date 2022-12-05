#!/usr/bin/env python
# coding: utf-8
"""read from jsonl score and write to relevant metadata json (e.g. 'id'.json)
python3 jsonlExtractTojson.py metadata/score.jsonl -o metadata/
"""
import argparse, os
from json import loads
from json import dump


def count_char(json, char):
    with open(json) as j:
        n = sum(l.count(char) for l in j)
    return n

def count_lines(json):
    with open(json) as j:
        for i, _ in enumerate(j, 1):
            pass
    return i


def get_keys(json, remove_dunder=True):
    keys = set()
    with open(json) as j:
        for l in j:
            d = loads(l)
            keys.update(d.keys())
    if remove_dunder:
        return {k for k in keys if k[:2] != '__'}
    return keys



def remove_dunder(d):
    """"""
    return {k: v for k, v in d.items() if k[:2] != '__'}


def main(args):

    target = args.output
    if args.filter is not None:
        filtering = True
        filenames = [os.path.splitext(file)[0] for file in os.listdir(args.filter)]
    else:
        filtering = False

    with open(args.file) as j:
        json_list = list(j)
        for json_str in json_list:
            try:
                result = loads(json_str)
            except Exception:
                print(f"Could not read this line as JSON:\n{json_str}")
                raise
            fname = result.get('id')
            #handle empty json
            if fname == None:
                print("Error for json: " + str(result))
                continue
            if filtering and fname not in filenames:
                if args.verbose:
                    print(f"Excluding ID {fname}.")
                continue
            curr = os.path.join(target, fname + '.json')
            if args.verbose:
                print(f"Writing {curr}")
            with open (curr, 'w', newline='') as jsonFile:
                dump(result,jsonFile)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description = """Convert JSONL file to json files.""")
    parser.add_argument('file',metavar='JSONL_FILE', help='Path to the JSONL file to be converted.')
    parser.add_argument('-o', '--output', metavar='json_FILE_DIR', help='DIR for json files.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Show more output.')
    parser.add_argument('--filter', metavar='ID_FILES_DIR', help='''In case you only want to output JSON files for IDs for which a file exists, pass
a directory containing files of which file names are IDs.''')
    # parser.add_argument('-d', '--dunder', action='store_false', help="Retain columns beginning with __ (dunder).")
    args = parser.parse_args()
    main(args)
