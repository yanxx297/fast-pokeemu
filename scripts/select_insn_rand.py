#!/usr/bin/env python

import os
import sys
import csv
import random
from collections import defaultdict

data = defaultdict(list);

def rawhexstr (str):
#     print str
    res = ""
    for s in str.split("\\x")[1:] :
        res += "\\\\x%s" % s
    return res

for idx, line in enumerate(csv.reader(open('instructions.csv', 'rb'), delimiter = '\t')):
    shellcode, _, insn, typ, _ = line;
    data[typ].append(shellcode)
    
for typ, x in data.iteritems():
    str = random.choice(x)
    print "%s\t%s" % (rawhexstr(str), typ)

    
    
    
