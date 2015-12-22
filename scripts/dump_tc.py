#!/usr/bin/python

import sys, os
from os.path import dirname, basename, abspath, join as joinpath, isfile
from common import *
import cpustate_x86
import elf

ROOT = abspath(joinpath(dirname(abspath(__file__)), ".."))
KERNEL = joinpath(ROOT, "Kernel/kernel")
kernel_elf = elf.Elf(KERNEL)

tc = kernel_elf.findSection(".testcase")
tc = (tc.getLowAddr(), tc.getHighAddr())
dump = cpustate_x86.load_dump(sys.argv[1])

print dump.mem.data[tc[0]:tc[1]]
