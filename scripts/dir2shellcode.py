#!/usr/bin/python

import sys
import common
import os


assert sys.argv[1].endswith("/exitstatus")
shellcode = sys.argv[1].split("/")[-2]
print common.to_c_str(shellcode)
