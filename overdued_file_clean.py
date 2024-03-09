import os
import sys
import shutil
import datetime
import re


def clean_path(path_str, _day_str):
    day_str_re = re.compile('^[\d]{8}')

    overdue_files = [x for x in os.listdir(path_str) if day_str_re.match(x) and x < _day_str]
    if overdue_files:
        print('find before day={} in path={}'.format(_day_str, path_str))
    else:
        print('no file before day={} in path={}'.format(_day_str, path_str))

    for f in overdue_files:
        file = os.path.join(path_str, f)
        if os.path.isdir(file):
            shutil.rmtree(file, ignore_errors=False)
            print('remove path before day={} in file={}'.format(_day_str, file))
        elif os.path.isfile(file):
            os.remove(file)
            print('remove file before day={} in file={}'.format(_day_str, file))


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        n = int(sys.argv[1])
        data_roots = sys.argv[2:]
    else:
        n = 30
        data_roots = ['/data']
    today = datetime.datetime.now()
    n_day_before = today + datetime.timedelta(days=-n)
    earliest_day_str = n_day_before.strftime('%Y%m%d')

    print(n, data_roots)
    for p in data_roots:
        clean_path(p, earliest_day_str)
