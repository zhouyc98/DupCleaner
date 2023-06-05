#!/usr/bin/env python3

import os
import sys
import glob
import time
from hashlib import sha256

IGNORE_DIRS = ('.git', '.svn')


def hash_file(filepath):
    with open(filepath, 'rb') as fp:
        txtb = fp.read()
    return sha256(txtb).hexdigest()


def str_size(size: float):
    if size < 1024 ** 2:
        return f'{size / 1024:.1f}KB'
    if size < 1024 ** 3:
        return f'{size / 1024 ** 2:.1f}MB'
    return f'{size / 1024 ** 3:.1f}GB'


def str_time(time: float):
    if time < 10:
        return f'{time:.2f}s'
    if time < 60:
        return f'{time:.1f}s'
    return f'{time / 60:.1f}min'


def is_valid_dir(path):
    # Return True if path is an existing directory, supporting wildcard
    return os.path.isdir(path) or len(glob.glob(path.rstrip('\\/') + '/'))


def scan_dup_files(dirpaths: list, ignore_size=10240):
    dirpaths = set(p for p in dirpaths if is_valid_dir(p))
    if not dirpaths: return []
    ignore_dirs = [os.path.sep + d + os.path.sep for d in IGNORE_DIRS]
    fndata = {}
    for dirpath in dirpaths:
        for filepath in glob.iglob(dirpath + '/**/*.*', recursive=True):
            if any(d in filepath for d in ignore_dirs): continue
            if not os.path.isfile(filepath) or os.path.islink(filepath): continue
            size = os.path.getsize(filepath)
            if size < ignore_size: continue
            ext = os.path.splitext(filepath)[1]
            if (ext, size) in fndata:
                if filepath in fndata[(ext, size)]: continue  # same filepath
                fndata[(ext, size)].append(filepath)
            else:
                fndata[(ext, size)] = [filepath]
    fngroups = [(size, fns) for (ext, size), fns in fndata.items() if len(fns) >= 2]

    fndata = {}
    for size, fns in fngroups:
        for fn in fns:
            h = hash_file(fn)
            if (size, h) in fndata:
                if os.path.samefile(fn, fndata[(size, h)][0]): continue  # hard link
                fndata[(size, h)].append(fn)
            else:
                fndata[(size, h)] = [fn]
    fngroups = [(size, fns) for (size, h), fns in fndata.items() if len(fns) >= 2]

    fngroups.sort(key=lambda v: v[0], reverse=True)
    for size, fns in fngroups: fns.sort(key=lambda fn: (fn, os.path.getmtime(fn)))
    return fngroups


def clean_dup_files(fngroups: list[tuple], use_hard_link=1):
    _link = os.link if use_hard_link else os.symlink
    for size, fns in fngroups:  # fns has been sorted by mtime
        fn_origin = os.path.abspath(fns[0])
        for fn in fns[1:]:
            os.remove(fn)
            _link(fn_origin, fn)
            print('linked', fn, '=' if use_hard_link else '->', fn_origin)


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print('Usage: python3 dupcleaner.py dirpath1 [dirpath2] [dirpath3]')
        exit()
    print('Scanning...')
    t = time.time()
    dup_file_groups = scan_dup_files(args)
    t = time.time() - t
    totalsize = 0
    dup_file_groups.reverse()  # reverse sort by size for print
    for size, fns in dup_file_groups:
        totalsize += size * (len(fns) - 1)
        print(f'{len(fns)} * {str_size(size)} duplicate files')
        for fn in fns:
            print('    ' + fn)
    print(f'\nFind {str_size(totalsize)} duplicate files, use {str_time(t)}')
    if not dup_file_groups:
        exit()
    try:
        c = input('Clean these duplicate files (h=hard_link/s=sym_link/[n=no])? ')
        if not (c and ('hard_link'.startswith(c) or 'sym_link'.startswith(c))):
            raise KeyboardInterrupt()
        print('\nCleaning...')
        clean_dup_files(dup_file_groups, c[0] == 'h')
    except KeyboardInterrupt:
        print('Exit')
