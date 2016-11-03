#!/usr/bin/env python
import os

splitlen = 1000
base = '/home/grad01/yan/Project/pokemu-oras/data/3_feistel-looping/single/qemu/out'

def split_file(file):
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

for subdir,dirs,files in os.walk(base):
    file = subdir + '/log'
#    print file
    split_file(file)
