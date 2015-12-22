#!/usr/bin/env python

import os, sys
from common import *

def gen_shellcode(testcase, disasm = False):
#    print "in gen_shellcode\n"
    shellcode = load_fuzzball_tc(testcase)["SHELLCODE"]
    #shellcode = shellcode + list("\x00")*(17 - len(shellcode))
    if disasm:
        print "%-32s\t%s" % (hexstr(shellcode), disasm(shellcode, 1))
    else:
        print "%s" % (hexstr(shellcode))


if __name__ == "__main__":
    for ktestfile in sys.argv[1:]:
        gen_shellcode(ktestfile)
