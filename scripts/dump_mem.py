#!/usr/bin/python

import sys, os
from os.path import dirname, basename, abspath, join as joinpath, isfile
from common import *
import cpustate_x86
import elf

ROOT = abspath(joinpath(dirname(abspath(__file__)), ".."))
KERNEL = joinpath(ROOT, "Kernel/kernel")
dump = cpustate_x86.load_dump(sys.argv[1])
base = int(sys.argv[2], 16)
size = int(sys.argv[3])
sys.stdout.write(dump.mem.data[base:base+size])
