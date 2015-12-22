#!/usr/bin/env python

import os, sys, random
from common import *

tc = {}

for l in sys.stdin.xreadlines():
    l = l.strip()
    shellcode, _, _, func, length = l.split("\t")
    length = int(length)
    shellcode = shellcode.replace("\\x", "")

    if length == 0:
	length = 6

    # skip fpu
    if func[0] == "F":
        continue

    try:
        tc[func] += [shellcode[:length*2]]
    except KeyError:
        tc[func] = [shellcode[:length*2]]

for k, v in tc.iteritems():
    print "%s\t%s" % (k, random.sample(v, 1)[0])
    
