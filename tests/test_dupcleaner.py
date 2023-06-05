import os
import shutil
import glob
import zipfile

import pytest

from dupcleaner.dupcleaner import *


class TestDupCleaner:
    def setup_method(self):
        shutil.rmtree('tests/data/data', True)
        with zipfile.ZipFile('tests/data/data.zip', 'r') as zf:
            zf.extractall('tests/data')

    def test_scan(self):
        assert len(scan_dup_files(['tests/data/data'], 100 * 1024)) == 0
        fngroups = scan_dup_files(['tests/data/data'])
        assert len(fngroups) == 3
        assert fngroups[0][0] == 69330
        assert len(fngroups[0][1]) == 4 and all(p[:-6].endswith('30') for p in fngroups[0][1])
        assert fngroups[1][0] == 46220
        assert len(fngroups[1][1]) == 4 and all(p[:-6].endswith('20') for p in fngroups[1][1])
        assert fngroups[2][0] == 23110
        assert len(fngroups[2][1]) == 4 and all(p[:-6].endswith('10') for p in fngroups[2][1])

    def test_clean_hard(self):
        fngroups = scan_dup_files(['tests/data/data'])
        assert len(fngroups)
        clean_dup_files(fngroups, 1)
        for n in ('10', '20', '30'):
            fns = glob.glob(f'tests/data/data/**/{n}-*.txt', recursive=True)
            assert len(fns) == 4 and all(not os.path.islink(f) for f in fns)
            assert len(set(os.stat(f).st_ino for f in fns)) == 1

    def test_clean_sym(self):
        fngroups = scan_dup_files(['tests/data/data'])
        assert len(fngroups)
        clean_dup_files(fngroups, 0)
        for n in ('10', '20', '30'):
            fns = glob.glob(f'tests/data/data/**/{n}-*.txt', recursive=True)
            assert len(fns) == 4 and len([f for f in fns if os.path.islink(f)]) == 3
            for f in fns[1:]: assert os.path.samefile(f, fns[0])

    def teardown_method(self):
        shutil.rmtree('tests/data/data', True)
