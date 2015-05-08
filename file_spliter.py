#!/usr/bin/python
# Filename : file_splitter.py

"""File Spliter
    Usage:
        split:
            file_spliter.py source_file size_per_part
        merge:
            file_spliter.py file_of_first_part
"""

'''
0. parse the args
1. split
1.1 open file
1.2 loop parts
1.2.1 set file name
1.2.2 write part to file

2. merge
2.1 parse first file header
2.2 get parts count
2.3 get raw file name
2.4 loop all part files
2.4.1 check header
2.4.2 merge into the total file buffer

file header:
FSR
current part
total parts
raw file name(length, value)
'''

import sys
import os
import io

from struct import pack
from struct import unpack

_g_split = True
_g_raw_file_name = ''
_g_part_size = 0
_g_part_count = 0

_g_file_type_string = 'FSR'


def _parse_file_header(file_name, first_part):
    global _g_file_type_string
    global _g_raw_file_name
    global _g_part_count

    file_name_without_type, file_name_type = os.path.splitext(file_name)

    _x_pos = file_name_without_type.rfind('_')
    if -1 == _x_pos:
        print("invalid file name, exit")
        sys.exit(10)

    tmp = file_name_without_type[_x_pos + 1:]
    _current_part_in_name = int(tmp)
    _raw_file_name_in_name = file_name_without_type[0:_x_pos]

    if '.' + _g_file_type_string.lower() != file_name_type:
        print("wrong file type, exit")
        sys.exit(11)

    try:
        f = open(file_name, 'rb')
    except IOError:
        print("failed to open file")
        sys.exit(10)

    # read the type string
    _type_str = f.read(3)
    if _g_file_type_string != _type_str:
        print("wrong file type, exit")
        f.close()
        sys.exit(12)

    # read parts
    _current_part = unpack("B", f.read(1))[0]
    _parts_count = unpack("B", f.read(1))[0]
    if _current_part >= _parts_count:
        print("invalid part, exit")
        f.close()
        sys.exit(13)

    if _current_part != _current_part_in_name:
        print("current part in name dose not match the file, exit")
        sys.exit(14)

    if first_part:
        if _current_part:
            print("first part must be 0, exit")
            f.close()
            sys.exit(15)

    # read raw file name
    _raw_file_name_length = unpack("B", f.read(1))[0]
    if _raw_file_name_length <= 0:
        print("invalid raw file name length, exit")
        f.close()
        sys.exit(16)

    _raw_file_name = f.read(_raw_file_name_length)
    if _raw_file_name != _raw_file_name_in_name:
        print("raw file name dose not match, exit")
        f.close()
        sys.exit(16)

    if first_part:
        _g_raw_file_name = _raw_file_name
        _g_part_count = _parts_count

    f.close()


def _get_options(argv):
    global _g_split
    global _g_raw_file_name
    global _g_part_size

    if 2 == len(argv):
        _g_split = True
    elif 1 == len(argv):
        _g_split = False
    else:
        print('invalid options count, exit')
        sys.exit(1)

    if _g_split:
        # split

        # get raw file name
        _g_raw_file_name = argv[0]

        # get part size
        # parse last char, get k and b
        _part_size_k = 1
        _part_size_b = 0
        _part_x = 0

        tail = argv[1][-1]
        if not tail.isalpha():
            _part_size_k = 10
            _part_size_b = int(tail)
        else:
            if 'K' == tail:
                _part_size_k = 1024
                _part_size_b = 0
            elif 'M' == tail:
                _part_size_k = 1024 * 1024
                _part_size_b = 0
            elif 'G' == tail:
                _part_size_k = 1024 * 1024 * 1024
                _part_size_b = 0
            else:
                print('invalid part size, exit')
                sys.exit(3)

        # parse head substring, get x
        if len(argv[1]) <= 1:
            _part_x = 0
        else:
            head = argv[1][0:-1]
            if not head.isdigit():
                print('invalid part size format, exit')
                sys.exit(4)
            _part_x = int(head)

        # calc part size
        _g_part_size = _part_size_k * _part_x + _part_size_b
        print('part size is: ' + str(_g_part_size))

    else:
        # merge
        _parse_file_header(argv[0], True)


def write_splited_file(raw_file_name, current_part, part_count, raw_file, current_pos, current_part_size):
    global _g_file_type_string

    # 0. set target file name
    target_file_name = raw_file_name + '_'
    target_file_name += "{:03d}".format(current_part)
    target_file_name += '.' + _g_file_type_string.lower()

    # 1. open target file
    try:
        tf = open(target_file_name, 'wb')
    except IOError:
        print("failed to open file")
        sys.exit(40)

    # 2. write target file header
    tf.write(_g_file_type_string)

    parsedata_part = pack("B", current_part)
    tf.write(parsedata_part)
    parsedata_part = pack("B", part_count)
    tf.write(parsedata_part)

    parsedata_part = pack("B", len(raw_file_name))
    tf.write(parsedata_part)
    tf.write(raw_file_name)

    # 3. write target file content
    raw_file.seek(current_pos, io.SEEK_SET)
    tf.write(raw_file.read(current_part_size))

    tf.close()


def split(raw_file_name, part_size):
    # 0. open file
    try:
        rf = open(raw_file_name, 'rb')
    except IOError:
        print("failed to open file")
        sys.exit(30)

    # 1. get file size, calc part count
    rf.seek(0, os.SEEK_END)
    _raw_file_size = rf.tell()
    _part_count = _raw_file_size / part_size
    if _raw_file_size % part_size:
        _part_count += 1

    # 2. loop, do split
    _current_pos = 0
    while _current_pos < _raw_file_size:
        # get current part size
        _current_part_size = part_size
        if _current_pos + part_size > _raw_file_size:
            _current_part_size = _raw_file_size - _current_pos

        write_splited_file(_g_raw_file_name, _current_pos / part_size, _part_count, rf, _current_pos, _current_part_size)

        _current_pos += _current_part_size
    else:
        print("end of raw file")
        rf.close()


def merge_into_file(target_file, raw_file_name, current_part):
    # 0. get current file name
    _current_file_name = raw_file_name + '_' + '{:03d}'.format(current_part) + '.' + _g_file_type_string.lower()

    # 1. parse file
    _parse_file_header(_current_file_name, False)

    _current_file_offset = 3 + 1 + 1 + 1 + len(raw_file_name)
    try:
        cf = open(_current_file_name, 'rb')
    except IOError:
        print("failed to open file")
        sys.exit(50)

    _current_file_size = os.stat(_current_file_name).st_size
    if _current_file_size <= _current_file_offset:
        print("invalid file size, exit")
        sys.exit(60)

    # 2. do merge
    cf.seek(_current_file_offset, io.SEEK_SET)
    target_file.write(cf.read(_current_file_size - _current_file_offset))

    cf.close()


def merge(raw_file_name):
    global _g_part_count

    # 0. open raw file
    try:
        tf = open(raw_file_name, 'wb')
    except IOError:
        print("failed to open file")
        sys.exit(50)

    # 1. loop, do merge
    _current_part = 0
    while _current_part < _g_part_count:
        merge_into_file(tf, raw_file_name, _current_part)
        _current_part += 1
    else:
        tf.close()

# 0. get the options
_get_options(sys.argv[1:])

# 1. make dirs
if _g_split:
    # do split
    print("start to split")
    split(_g_raw_file_name, _g_part_size)
    print("file splitted")
else:
    # do merge
    print("start to merge")
    merge(_g_raw_file_name)
    print("files merged")
