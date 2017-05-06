#!/usr/bin/env python
import os
import sys

def split_file(file, splitlen):
    if not os.path.isfile(file):
        return
    input = open(file, 'r').read().split(',')
    idx = 0
    for val in range(0, len(input), splitlen):
        data = input[val:val+splitlen]
        name = os.path.dirname(file) + "/%d.log" % idx
        print name
        output = open(name, 'w')
        output.write(','.join(data))
        output.close()
        idx += 1

if __name__ == "__main__":
    filename = sys.argv[1]
    splitlen = sys.argv[2]
    split_file(filename, int(splitlen))
