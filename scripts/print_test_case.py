#!/usr/bin/env python

import sys, os
from common import *

def hexstr(s):
    r = ""
    for c in s:
        if c is not None:
            r += "\\x%.2x" % ord(c)
        else:
            r += "??"
    return r

first = True
for f in sys.argv[1:]:
    tc = load_fuzzball_tc(f, full = True)

    if not first: print ""
    f = " %s " % f
    pad = (columns() - len(f)) / 2
    print "*"*pad + f + "*"*pad
    for (_, k), (v, s) in tc.iteritems():
        print "  %-32s --->  %s" % ("%s (%s)" % (k, s), hexstr(v))

    first = False
