#!/usr/bin/env python

import os
from os.path import dirname, basename, abspath, join as joinpath, isfile
import sys
import struct
import random
from random import choice
import subprocess
import time
import tempfile as tempfile_
import networkx
import elf
import StringIO
import hashlib
import cpustate_x86
import math

localpath = os.path.expanduser("~/.local/lib/python2.7/site-packages") 
sys.path.append(localpath)

from common import *
# from numpy.f2py.f2py_testing import cmdline
# from telnetlib import theNULL
import binascii
# from cups import Dest
# from scipy.special.basic import pbdn_seq
#from statsmodels.regression.tests.test_quantile_regression import idx
import code
# from sympy.galgebra.printing import prog_str

sys.path.append("../tools/pyxed")
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "tools", "pyxed"))
import pyxed



ROOT = abspath(joinpath(dirname(abspath(__file__)), ".."))
KERNEL = joinpath(ROOT, "kernel")
GRUB = joinpath(ROOT, "grub_stuff")
GRUB_EXE = joinpath(ROOT, "scripts/grub")
SNAPSHOT = joinpath(ROOT, "base.snap")
TESTCASE = ".testcase"
NULL = open("/dev/null", "w")
FLOPPY_TEMPLATE = "/tmp/gen-floppy-image.template"
DEBUG = 2

# ===-----------------------------------------------------------------------===
# MODE:
# 0: single test case mode
# 1: simple aggregating mode
# 2: feistel mode
# 3: feistel loopping 
# ===-----------------------------------------------------------------------===
MODE = 0

# ===-----------------------------------------------------------------------===
# Whether Paging is on
# ===-----------------------------------------------------------------------===
PG = 1

# ===-----------------------------------------------------------------------===
# Range for additional memory access
# ===-----------------------------------------------------------------------===
retseg = "fs"         # Selector of the segment used for return point updating
retp = 0x128d008      # The location to store current return point for ecpt handler
edata = retp + 4      # Starting address of exception data
next_addr = edata + 8
start_addr = next_addr
end_addr = 0x013fffff

# ===-----------------------------------------------------------------------===
# Container for feistel R & l blocks
# NOTE: 
# count_r and count_l increase from 0 during the generating process of each test case
# The length of feistel_r and feistel_l only updated while generating the 1st test case
# ===-----------------------------------------------------------------------===  
init_r = []         #gadgets that copy input of first instruction to R block
init_l = []         #gadgets that copy random value to L block 
feistel_r = []      #R block address container
feistel_r_bak = []  #backup of R block
feistel_l = []      #L block container
feistel_in = []     #Backup original inputs for restoring at the end of each TC
feistel_out = []    #Backup original outputs for restoring at the end of each TC
count_r = 0         # Pointer to the current R/L block
count_l = 0
count_addr = 0      # A mem location to store loop count
LOOP = 1            #repeat testing each test case for a number of times


# ===-----------------------------------------------------------------------===
# Other global variables
# ===-----------------------------------------------------------------------===
l_insn = None       # Label at the tested instruction
l_restore = []      # list of inputs/outputs for which a pair of backup/restore
                    # gadgets has been generated; keep this list so that each 
                    # location only reset at most once
in_to_reg = dict()  # memory operand as input -> registers involved
out_to_reg = dict() # memory operand as output -> registers involved

def in_dict(reg, d):
    reglist = [["eax", "ax", "ah", "al"], ["ebx", "bx", "bh", "bl"], \
            ["ecx", "cx", "ch", "cl"], ["edx", "dx", "dh", "dl"]]
    if reg in d:
        return True
    else:
        for l in reglist:
            if reg in l:
                for e in d:
                    if e in l:
                        return True
    return False

# ===-----------------------------------------------------------------------===
# Generate a random number or use a constant value to L0
# ===-----------------------------------------------------------------------===
def gen_seed(rand = True):
    if rand:
        return random.randint(0, 0xffffffff)
    else:
        return 0xabcef801
    
    
# ===-----------------------------------------------------------------------===
# Flip random address range and addresses of feistel block from pagin on to off
# or from off to on (depends on current status)
# ===-----------------------------------------------------------------------===
def flip_addrs():
    global init_r
    global feistel_r
    global feistel_r_bak
    global feistel_l
    global feistel_in
    global count_addr
    global next_addr
    global start_addr
    global end_addr
    global retp
    global edata
    
    def flip_list(l):
        for idx, val in enumerate(l):
            l[idx] = val ^ 0x01000000
    
    flip_list(feistel_r)
    flip_list(feistel_r_bak)
    flip_list(feistel_l)
    flip_list(feistel_in)
    retp = retp ^ 0x01000000
    edata = edata ^ 0x01000000
    count_addr = count_addr ^ 0x01000000
    next_addr = next_addr ^ 0x01000000
    start_addr = start_addr ^ 0x01000000
    end_addr = end_addr ^ 0x01000000    
            

# ===-----------------------------------------------------------------------===
# Print a list of addresses `l` as one row of a table
# ===-----------------------------------------------------------------------===
def print_line(title, l):    
    str = " %s\t" % title
    for i in l:
        str += "0x%.8x " % i
    print str
    
    
# ===-----------------------------------------------------------------------===
# Print feistel blocks in user-friendly style
# ===-----------------------------------------------------------------------===
def print_feistel_blocks():
#     assert(len(feistel_r) == len(feistel_l))
    print "\n"
    print "Feistel Blocks: %d" % len(feistel_r)
    print_line("R", feistel_r)
    print_line("R_bak", feistel_r_bak)
    print_line("L", feistel_l)
    print_line("in_bak", feistel_in)
    print_line("out_bak", feistel_out)
    print "\n"


reg_map = {
        pyxed.XED_REG_INVALID : "",
        pyxed.XED_REG_BNDCFGU : "bndcfgu",
        pyxed.XED_REG_BNDSTATUS: "bndstatus",
        pyxed.XED_REG_BND0 : "bnd0",
        pyxed.XED_REG_BND1 : "bnd1",
        pyxed.XED_REG_BND2 : "bnd2",
        pyxed.XED_REG_BND3 : "bnd3",
        pyxed.XED_REG_CR0 :"cr0",
        pyxed.XED_REG_CR1 : "cr1",
        pyxed.XED_REG_CR2 : "cr2",
        pyxed.XED_REG_CR3 : "cr3",
        pyxed.XED_REG_CR4 : "cr4",
        pyxed.XED_REG_CR5 : "cr5",
        pyxed.XED_REG_CR6 : "cr6",
        pyxed.XED_REG_CR7 : "cr7",
        pyxed.XED_REG_CR8 : "cr8",
        pyxed.XED_REG_CR9 : "cr9",
        pyxed.XED_REG_CR10 : "cr10",
        pyxed.XED_REG_CR11 : "cr11",
        pyxed.XED_REG_CR12 : "cr12",
        pyxed.XED_REG_CR13 : "cr13",
        pyxed.XED_REG_CR14 : "cr14",
        pyxed.XED_REG_CR15 : "cr15",
        pyxed.XED_REG_DR0 : "dr0",
        pyxed.XED_REG_DR1 : "dr1",
        pyxed.XED_REG_DR2 : "dr2",
        pyxed.XED_REG_DR3 : "dr3",
        pyxed.XED_REG_DR4 : "dr4",
        pyxed.XED_REG_DR5 : "dr5",
        pyxed.XED_REG_DR6 : "dr6",
        pyxed.XED_REG_DR7 : "dr7",
        pyxed.XED_REG_FLAGS : "flags",
        pyxed.XED_REG_EFLAGS : "eflags",
        pyxed.XED_REG_RFLAGS : "rflags",
        pyxed.XED_REG_AX : "ax",
        pyxed.XED_REG_CX : "cx",
        pyxed.XED_REG_DX : "dx",
        pyxed.XED_REG_BX : "bx",
        pyxed.XED_REG_SP : "sp",
        pyxed.XED_REG_BP : "bp",
        pyxed.XED_REG_SI : "si",
        pyxed.XED_REG_DI : "di",
        pyxed.XED_REG_R8W : "r8w",
        pyxed.XED_REG_R9W : "r9w",
        pyxed.XED_REG_R10W : "r10w",
        pyxed.XED_REG_R11W : "r11w",
        pyxed.XED_REG_R12W : "r12w",
        pyxed.XED_REG_R13W : "r13w",
        pyxed.XED_REG_R14W : "r14w",
        pyxed.XED_REG_R15W : "r15w",
        pyxed.XED_REG_EAX : "eax",
        pyxed.XED_REG_ECX : "ecx",
        pyxed.XED_REG_EDX : "edx",
        pyxed.XED_REG_EBX : "ebx",
        pyxed.XED_REG_ESP : "esp",
        pyxed.XED_REG_EBP : "ebp",
        pyxed.XED_REG_ESI : "esi",
        pyxed.XED_REG_EDI : "edi",
        pyxed.XED_REG_R8D : "r8d",
        pyxed.XED_REG_R9D : "r9d",
        pyxed.XED_REG_R10D : "r10d",
        pyxed.XED_REG_R11D : "r11d",
        pyxed.XED_REG_R12D : "r12d",
        pyxed.XED_REG_R13D : "r13d",
        pyxed.XED_REG_R14D : "r14d",
        pyxed.XED_REG_R15D : "r15d",
        pyxed.XED_REG_RAX : "rax",
        pyxed.XED_REG_RCX : "rcx",
        pyxed.XED_REG_RDX : "rdx",
        pyxed.XED_REG_RBX : "rbx",
        pyxed.XED_REG_RSP : "rsp",
        pyxed.XED_REG_RBP : "rbp",
        pyxed.XED_REG_RSI : "rsi",
        pyxed.XED_REG_RDI : "rdi",
        pyxed.XED_REG_R8 : "r8",
        pyxed.XED_REG_R9 : "r9",
        pyxed.XED_REG_R10 : "r10",
        pyxed.XED_REG_R11 : "r11",
        pyxed.XED_REG_R12 : "r12",
        pyxed.XED_REG_R13 : "r13",
        pyxed.XED_REG_R14 : "r14",
        pyxed.XED_REG_R15 : "r15",
        pyxed.XED_REG_AL: "al",
        pyxed.XED_REG_CL : "cl",
        pyxed.XED_REG_DL : "dl",
        pyxed.XED_REG_BL : "bl",
        pyxed.XED_REG_SPL : "spl",
        pyxed.XED_REG_BPL : "bpl",
        pyxed.XED_REG_SIL : "sil",
        pyxed.XED_REG_DIL : "dil",
        pyxed.XED_REG_R8B : "r8b",
        pyxed.XED_REG_R9B : "r9b",
        pyxed.XED_REG_R10B : "r10b",
        pyxed.XED_REG_R11B : "r11b",
        pyxed.XED_REG_R12B : "r12b",
        pyxed.XED_REG_R13B : "r13b",
        pyxed.XED_REG_R14B : "r14b",
        pyxed.XED_REG_R15B : "r15b",
        pyxed.XED_REG_AH : "ah",
        pyxed.XED_REG_CH : "ch",
        pyxed.XED_REG_DH : "dh",
        pyxed.XED_REG_BH : "bh",
        pyxed.XED_REG_ERROR : "error",
        pyxed.XED_REG_RIP : "rip",
        pyxed.XED_REG_EIP : "eip",
        pyxed.XED_REG_IP : "ip",
        pyxed.XED_REG_K0 : "k0",
        pyxed.XED_REG_K1 : "k1",
        pyxed.XED_REG_K2 : "k2",
        pyxed.XED_REG_K3 : "k3",
        pyxed.XED_REG_K4 : "k4",
        pyxed.XED_REG_K5 : "k5",
        pyxed.XED_REG_K6 : "k6",
        pyxed.XED_REG_K7 : "k7",
        pyxed.XED_REG_MMX0 : "mm0",
        pyxed.XED_REG_MMX1 : "mm1",
        pyxed.XED_REG_MMX2 : "mm2",
        pyxed.XED_REG_MMX3 : "mm3",
        pyxed.XED_REG_MMX4 : "mm4",
        pyxed.XED_REG_MMX5 : "mm5",
        pyxed.XED_REG_MMX6 : "mm6",
        pyxed.XED_REG_MMX7 : "mm7",
        #pyxed.XED_REG_SSP : "ssp",
        #pyxed.XED_REG_IA32_U_CET : "",
        pyxed.XED_REG_MXCSR : "mxcsr",
        pyxed.XED_REG_STACKPUSH : "",
        pyxed.XED_REG_STACKPOP : "",
        pyxed.XED_REG_GDTR : "gdtr",
        pyxed.XED_REG_LDTR : "ldtr",
        pyxed.XED_REG_IDTR: "idtr",
        pyxed.XED_REG_TR : "tr",
        pyxed.XED_REG_TSC : "tsc",
        pyxed.XED_REG_TSCAUX : "tscaux",
        pyxed.XED_REG_MSRS : "msrs",
        pyxed.XED_REG_FSBASE : "fsbase",
        pyxed.XED_REG_GSBASE : "gsbase",
        pyxed.XED_REG_X87CONTROL : "x87control",
        pyxed.XED_REG_X87STATUS : "x87status",
        pyxed.XED_REG_X87TAG : "x87tag",
        pyxed.XED_REG_X87PUSH : "x87push",
        pyxed.XED_REG_X87POP : "x87pop",
        pyxed.XED_REG_X87POP2 : "x87pop2",
        pyxed.XED_REG_X87OPCODE : "x87opcode",
        pyxed.XED_REG_X87LASTCS : "x87lastcs",
        pyxed.XED_REG_X87LASTIP : "x87lastip",
        pyxed.XED_REG_X87LASTDS : "x87lastds",
        pyxed.XED_REG_X87LASTDP : "x87lastdp",
        pyxed.XED_REG_CS : "cs",
        pyxed.XED_REG_DS : "ds",
        pyxed.XED_REG_ES : "es",
        pyxed.XED_REG_SS : "ss",
        pyxed.XED_REG_FS : "fs",
        pyxed.XED_REG_GS : "gs",
        pyxed.XED_REG_TMP0 : "tmp0",
        pyxed.XED_REG_TMP1 : "tmp1",
        pyxed.XED_REG_TMP2 : "tmp2",
        pyxed.XED_REG_TMP3 : "tmp3",
        pyxed.XED_REG_TMP4 : "tmp4",
        pyxed.XED_REG_TMP5 : "tmp5",
        pyxed.XED_REG_TMP6 : "tmp6",
        pyxed.XED_REG_TMP7 : "tmp7",
        pyxed.XED_REG_TMP8 : "tmp8",
        pyxed.XED_REG_TMP9 : "tmp9",
        pyxed.XED_REG_TMP10 : "tmp10",
        pyxed.XED_REG_TMP11 : "tmp11",
        pyxed.XED_REG_TMP12 : "tmp12",
        pyxed.XED_REG_TMP13 : "tmp13",
        pyxed.XED_REG_TMP14 : "tmp14",
        pyxed.XED_REG_TMP15 : "tmp15",
        pyxed.XED_REG_ST0 : "st(0)",
        pyxed.XED_REG_ST1 : "st(1)",
        pyxed.XED_REG_ST2 : "st(2)",
        pyxed.XED_REG_ST3 : "st(3)",
        pyxed.XED_REG_ST4 : "st(4)",
        pyxed.XED_REG_ST5 : "st(5)",
        pyxed.XED_REG_ST6 : "st(6)",
        pyxed.XED_REG_ST7 : "st(7)",
        pyxed.XED_REG_XCR0 : "xcr0",
        pyxed.XED_REG_XMM0 : "xmm0",
        pyxed.XED_REG_XMM1 : "xmm1",
        pyxed.XED_REG_XMM2 : "xmm2",
        pyxed.XED_REG_XMM3 : "xmm3",
        pyxed.XED_REG_XMM4 : "xmm4",
        pyxed.XED_REG_XMM5 : "xmm5",
        pyxed.XED_REG_XMM6 : "xmm6",
        pyxed.XED_REG_XMM7 : "xmm7",
        pyxed.XED_REG_XMM8 : "xmm8",
        pyxed.XED_REG_XMM9 : "xmm9",
        pyxed.XED_REG_XMM10 : "xmm10",
        pyxed.XED_REG_XMM11 : "xmm11",
        pyxed.XED_REG_XMM12 : "xmm12",
        pyxed.XED_REG_XMM13 : "xmm13",
        pyxed.XED_REG_XMM14 : "xmm14",
        pyxed.XED_REG_XMM15 : "xmm15",
        pyxed.XED_REG_XMM16 : "xmm16",
        pyxed.XED_REG_XMM17 : "xmm17",
        pyxed.XED_REG_XMM18 : "xmm18",
        pyxed.XED_REG_XMM19 : "xmm19",
        pyxed.XED_REG_XMM20 : "xmm20",
        pyxed.XED_REG_XMM21 : "xmm21",
        pyxed.XED_REG_XMM22 : "xmm22",
        pyxed.XED_REG_XMM23 : "xmm23",
        pyxed.XED_REG_XMM24 : "xmm24",
        pyxed.XED_REG_XMM25 : "xmm25",
        pyxed.XED_REG_XMM26 : "xmm26",
        pyxed.XED_REG_XMM27 : "xmm27",
        pyxed.XED_REG_XMM28 : "xmm28",
        pyxed.XED_REG_XMM29 : "xmm29",
        pyxed.XED_REG_XMM30 : "xmm30",
        pyxed.XED_REG_XMM31 : "xmm31",
        pyxed.XED_REG_YMM0 : "ymm0",
        pyxed.XED_REG_YMM1 : "ymm1",
        pyxed.XED_REG_YMM2 : "ymm2",
        pyxed.XED_REG_YMM3 : "ymm3",
        pyxed.XED_REG_YMM4 : "ymm4",
        pyxed.XED_REG_YMM5 : "ymm5",
        pyxed.XED_REG_YMM6 : "ymm6",
        pyxed.XED_REG_YMM7 : "ymm7",
        pyxed.XED_REG_YMM8 : "ymm8",
        pyxed.XED_REG_YMM9 : "ymm9",
        pyxed.XED_REG_YMM10 : "ymm10",
        pyxed.XED_REG_YMM11 : "ymm11",
        pyxed.XED_REG_YMM12 : "ymm12",
        pyxed.XED_REG_YMM13 : "ymm13",
        pyxed.XED_REG_YMM14 : "ymm14",
        pyxed.XED_REG_YMM15 : "ymm15",
        pyxed.XED_REG_YMM16 : "ymm16",
        pyxed.XED_REG_YMM17 : "ymm17",
        pyxed.XED_REG_YMM18 : "ymm18",
        pyxed.XED_REG_YMM19 : "ymm19",
        pyxed.XED_REG_YMM20 : "ymm20",
        pyxed.XED_REG_YMM21 : "ymm21",
        pyxed.XED_REG_YMM22 : "ymm22",
        pyxed.XED_REG_YMM23 : "ymm23",
        pyxed.XED_REG_YMM24 : "ymm24",
        pyxed.XED_REG_YMM25 : "ymm25",
        pyxed.XED_REG_YMM26 : "ymm26",
        pyxed.XED_REG_YMM27 : "ymm27",
        pyxed.XED_REG_YMM28 : "ymm28",
        pyxed.XED_REG_YMM29 : "ymm29",
        pyxed.XED_REG_YMM30 : "ymm30",
        pyxed.XED_REG_YMM31 : "ymm31",
        pyxed.XED_REG_ZMM0 : "zmm0",
        pyxed.XED_REG_ZMM1 : "zmm1",
        pyxed.XED_REG_ZMM2 : "zmm2",
        pyxed.XED_REG_ZMM3 : "zmm3",
        pyxed.XED_REG_ZMM4 : "zmm4",
        pyxed.XED_REG_ZMM5 : "zmm5",
        pyxed.XED_REG_ZMM6 : "zmm6",
        pyxed.XED_REG_ZMM7 : "zmm7",
        pyxed.XED_REG_ZMM8 : "zmm8",
        pyxed.XED_REG_ZMM9 : "zmm9",
        pyxed.XED_REG_ZMM10 : "zmm10",
        pyxed.XED_REG_ZMM11 : "zmm11",
        pyxed.XED_REG_ZMM12 : "zmm12",
        pyxed.XED_REG_ZMM13 : "zmm13",
        pyxed.XED_REG_ZMM14 : "zmm14",
        pyxed.XED_REG_ZMM15 : "zmm15",
        pyxed.XED_REG_ZMM16 : "zmm16",
        pyxed.XED_REG_ZMM17 : "zmm17",
        pyxed.XED_REG_ZMM18 : "zmm18",
        pyxed.XED_REG_ZMM19 : "zmm19",
        pyxed.XED_REG_ZMM20 : "zmm20",
        pyxed.XED_REG_ZMM21 : "zmm21",
        pyxed.XED_REG_ZMM22 : "zmm22",
        pyxed.XED_REG_ZMM23 : "zmm23",
        pyxed.XED_REG_ZMM24 : "zmm24",
        pyxed.XED_REG_ZMM25 : "zmm25",
        pyxed.XED_REG_ZMM26 : "zmm26",
        pyxed.XED_REG_ZMM27 : "zmm27",
        pyxed.XED_REG_ZMM28 : "zmm28",
        pyxed.XED_REG_ZMM29 : "zmm29",
        pyxed.XED_REG_ZMM30 : "zmm30",
        pyxed.XED_REG_ZMM31 : "zmm31",
        pyxed.XED_REG_LAST : ""
}

prefix = ["es",
          "ss",
          "fs",
          "gs",
          "cs",
          "ds",
          "data16",
          "addr16",
          "lock",
          "repnz",
          "repz"]


# Obsoleted container for feistel R & l blocks
l_hi = "0x%x" % random.randint(0x00218008, 0x003fffff)
l_hi_backup = "0x%x" % random.randint(0x00218008, 0x003fffff)
l_lo = "0x%x" % random.randint(0x00218008, 0x003fffff)
l_lo_backup = "0x%x" % random.randint(0x00218008, 0x003fffff)
r_hi = "0x%x" % random.randint(0x00218008, 0x003fffff)
r_lo = "0x%x" % random.randint(0x00218008, 0x003fffff)

# ===-----------------------------------------------------------------------===
# Return true if the symbolic variable represents a memory location
# ===-----------------------------------------------------------------------===
def ismem(s):
    return s[0] == "mem"


# ===-----------------------------------------------------------------------===
# Return true if the symbolic variable represents a general purpose register
# ===-----------------------------------------------------------------------===
def isreg(s):
    return s[0] == "reg"


# ===-----------------------------------------------------------------------===
# Return true if the symbolic variable represents a segment register
# ===-----------------------------------------------------------------------===
def issreg(s):
    return s[0] == "sreg"


# ===-----------------------------------------------------------------------===
# Return true if the symbolic variable represents a control register
# ===-----------------------------------------------------------------------===
def iscreg(s):
    return s[0] == "creg"



# ===-----------------------------------------------------------------------===
# Return true if the symbolic variable represents a debug register
# ===-----------------------------------------------------------------------===
def isdreg(s):
    return s[0] == "dreg"


def isgdt(s):
    return s.startswith("GDT_")


def mkreg(r):
    return "reg", r

def mksreg(r):
    return "sreg", r

def mkmem(m):
    return "mem", m

# ===-----------------------------------------------------------------------===
# Return the original content of a given register
# ===-----------------------------------------------------------------------===
def in_snapshot_reg(what, snapshot):
    what = "R" + what[1:]
    return getattr(snapshot.cpus[0].regs_state, what.lower())
    
def in_snapshot_sreg(what, snapshot):
    return getattr(snapshot.cpus[0].sregs_state, what.lower()).selector

def in_snapshot_creg(what, snapshot):
    return getattr(snapshot.cpus[0].sregs_state, what.lower())
    
in_snapshot_dreg = in_snapshot_sreg

# ===-----------------------------------------------------------------------===
# Return the original content of a certain memory location
# ===-----------------------------------------------------------------------===
def in_snapshot_mem(what, snapshot):
    (addr, size) = what
    return snapshot.mem.data[addr:addr+size]


# ===-----------------------------------------------------------------------===
# Symplify symbol's information (used for dependency tracking)
# ===-----------------------------------------------------------------------===
def strip(sym):
    if sym.startswith("GDT_"):
        sym = sym.split("_")
        return sym[0] + "_" + sym[1]
    else:
        return sym
    
# ===-------------------------------------------------------------------===
# Return true if str contains a pair of "()"
# ===-------------------------------------------------------------------===
def parentheses(str):
    l1 = str.find("(")
    l2 = str.find(")")
    if l2 > l1 and l1 >= 0:
        return True
    else:
        return False    

# ===-------------------------------------------------------------------===
# Given a gadget list `l`, append gadget `ext` after each gadget in it
# and return the appended list
# ===-------------------------------------------------------------------===
def append_gadget(l, ext):
    out = []
#     print "append_gadget    l[%d]" % len(l)
    for s in l:
        b = ext[:]
        b.insert(0, s)
        out += b
    return out


# ===-------------------------------------------------------------------===
# Remvoe all the Nonetypes of a given list
# ===-------------------------------------------------------------------===
def remove_none(l):
    return [x for x in l if x is not None]


# ===-------------------------------------------------------------------===
# Generate a (list of) new memory addresses either randomly or in order
# For a variable longer than 32 bits, this script will allocate multipe 32-
# bit memory locations.
# ===-------------------------------------------------------------------===
def get_addr(s = 4, is_rand = False):
    global next_addr
    size = int(math.ceil(float(s)/4)*4)

    addr = []
    if is_rand:
        addr = [choice(range(start_addr, end_addr,size))]
        for i in range(1, size/4):
            addr += [addr[i-1] + 4]          
    else:
        addr = [next_addr]
        for i in range(1, size/4):
            addr += [addr[i-1] + 4]
        next_addr += size
        assert(next_addr <= end_addr)
    
    if DEBUG >= 3:
        l = ""
        for i in range(0, len(addr)):
            l += "0x%x " % addr[i]        
        print "get_addr    round size: %d -> %d" % (s, int(size))
        print "get_addr    %s" % l
    
    return addr  

        
def is_valid(op):
    if op.endswith('_INVALID') or op.endswith('_LAST'):
        return False
    return True

def make_stable(l, done, snapshot):
    # Need one or more extra passes to define what has been killed but not
    # defined
    l_ = l[:]
    stable = False
    while not stable:
        stable = True
    
        killed = set()
        defined = set()
        for g in l:
            killed |= g.kill
            defined |= g.define
    
        if len(killed - defined):
            print "Forcing gadgets for: ", \
                    ", ".join([str(v) for v in killed - defined])
    
        for rm in killed - defined:
            assert rm not in done
            stable = False
            rm.value = rm.in_snapshot(snapshot)
            l_ += rm.gen_gadget(snapshot)
        return l_


def get_visibility(op):
    vis = '?'
    for v in dir(pyxed):
        if v.startswith('XED_OPVIS_') and getattr(pyxed, v) == op:
            vis = v
            break    
    return vis


def is_explicit(op):
    vis = get_visibility(op)
    if vis == 'XED_OPVIS_EXPLICIT': 
        return True
    else:
        return False

def get_category(op):
    category = '?'
    for c in dir(pyxed):
        if c.startswith('XED_CATEGORY_') and getattr(pyxed, c) == op:
            category = c
            break
    return category

def get_iclass(op):
    iclass = '?'
    for c in dir(pyxed):
        if c.startswith('XED_ICLASS_') and getattr(pyxed, c) == op:
            iclass = c
            break
    return iclass


def get_reg_name(reg):
    reg_name = '?'
    for name in dir(pyxed):
        if name.startswith('XED_REG_') and getattr(pyxed, name) == reg:
#         if getattr(pyxed, name) == reg:
            reg_name = name
            break
    return reg_name


def get_operand_name(op):
    op_name = '?'
    for name in dir(pyxed):
        if name.startswith('XED_OPERAND_') and getattr(pyxed, name) == op:
            op_name = name
            break
    return op_name

def get_tag(t):
    tag = '?'
    for name in dir(pyxed):
        if name.startswith('XED_') and getattr(pyxed, name) == t:
            tag = name
            break
    return tag


# ===-------------------------------------------------------------------===
# Convert size to a proper mov instruction
# ===-------------------------------------------------------------------===
def size2mov(size, r):
    op = ""
    if r.startswith("mm"):
        return "movd"
    elif r.startswith("xmm"):
        return "movdqu"
    elif size == 1:
        op = "movb"
    elif size == 2:
        op = "movw"
    elif size == 4:
        op = "movl"
    elif size == 8:
        op = "movd"
    elif size == 16:
        op = "movdqu"
    else:
        assert 0, "Illegal register size (%d) as a mov target" % size
    return op


# ===-------------------------------------------------------------------===
# Convert size to a proper xor instruction
# ===-------------------------------------------------------------------===
def size2xor(size, r):
    op = ""
    if r.startswith("mm") or r.startswith("xmm"):
        return "pxor"
    elif size <= 4:
        op = "xor"
    elif size <= 16:
        op = "pxor"
    else:
        assert 0, "Illegal register size as a xor target"
    return op



# ===-------------------------------------------------------------------===
# Floating point version size2mov
# ===-------------------------------------------------------------------===
def fsize2mov(size, r):
    op = ""
    if r.startswith("mm"):
        return "movd"
    elif r.startswith("xmm"):
        return "movdqu"
    elif size == 1:
        op = "movb"
    elif size == 2:
        op = "movw"
    elif size == 4:
        op = "movl"
    elif size == 8:
        op = "movd"
    elif size == 16:
        op = "movdqu"
    else:
        assert 0, "Illegal register size (%d) as a mov target" % size
    return op


# ===-------------------------------------------------------------------===
# Floating point version size2xor
# ===-------------------------------------------------------------------===
def fsize2xor(size, r):
    op = ""
    if r.startswith("mm") or r.startswith("xmm"):
        return "pxor"
    elif size <= 4:
        op = "xor"
    elif size <= 16:
        op = "pxor"
    else:
        assert 0, "Illegal register size as a xor target"
    return op


# ===-------------------------------------------------------------------===
# Given a register `r`, convert it to the same register of `size` long 
# NOTE: currenly support general registers only; Add support to other regs on demand
# ===-------------------------------------------------------------------===
def resize_reg(r, size = 4):
    reg = r
    try:        
        if r in ["eax", "ax", "al", "ah"]:
            if size == 1:
                reg = "al"
            elif size == 2:
                reg = "ax"
            elif size == 4:
                reg = "eax"
            else:
                raise Exception('EAX', size)
        elif r in ["ebx", "bx", "bl", "bh"]:
            if size == 1:
                reg = "bl"
            elif size == 2:
                reg = "bx"
            elif size == 4:
                reg = "ebx"
            else:
                raise Exception('EBX', size)
        if r in ["ecx", "cx", "cl", "ch"]:
            if size == 1:
                reg = "cl"
            elif size == 2:
                reg = "cx"
            elif size == 4:
                reg = "ecx"
            else:
                raise Exception('ECX', size)                        
        if r in ["edx", "dx", "dl", "dh"]:
            if size == 1:
                reg = "dl"
            elif size == 2:
                reg = "dx"
            elif size == 4:
                reg = "edx"
            else:
                raise Exception('EDX', size)
        if r in ["esi", "si"]:
            if size == 2:
                reg = "si"
            elif size == 4:
                reg = "esi"
            else:
                raise Exception('ESI', size)
        if r in ["edi", "di"]:
            if size == 2:
                reg = "di"
            elif size == 4:
                reg = "edi"
            else:
                raise Exception('EDI', size)
        if r in ["ebp", "bp"]:
            if size == 2:
                reg = "bp"
            elif size == 4:
                reg = "ebp"
            else:
                raise Exception('EBP', size)
        if r in ["esp", "sp"]:
            if size == 2:
                reg = "sp"
            elif size == 4:
                reg = "esp"
            else:
                raise Exception('ESP', size)
    except Exception as (e, s):
        assert 0, "Illegal register size - %s size %d" % (e, s)
    return reg


# ===-------------------------------------------------------------------===
# Generate code that store eip in register `r`
# Currently not in use, since eip is ignored
# Note that the eip it stored it the eip of the next instruction after itself
# ===-------------------------------------------------------------------===
def gen_get_eip(r, r2 = None):
    l1 = random.randint(0, 0xffffffff)
    l2 = r2 if r2 is not None else random.randint(0, 0xffffffff)
    asm = "jmp forward_%.8x;" \
        "forward_%.8x:" \
        "mov (%%esp),%%%s;" \
        "ret;" \
        "forward_%.8x: " \
        "call forward_%.8x;" % (l2, l1, r, l2, l1)
    return asm

# ===-------------------------------------------------------------------===
# Generate code in text format to compare a reg/mem with a constant
# ===-------------------------------------------------------------------===
def gen_cmp_imm(src, imm, t = "eax", size = 4):
    asm = ""
    if src in reg_map.values():
        reg = src
        if reg == "eflags":
            asm += "pushf;" \
                "pop %%%s;" \
                "cmpl $0x%x,%%%s;" % (t, imm, t)
        elif reg in ["eip", "ip"]:
            asm += gen_get_eip(t)
            asm += "cmpl $0x%x,%%%s;" % (imm, t)
        elif reg == "mxcsr":
            m = get_addr(4, True)[0]
            asm += "ldmxcsr %s;" \
                    "mov %s,%%%s;" \
                    "cmp $0x%x,%%%s;"% (m, m, t, imm, t)
        elif reg.startswith("cr") or reg.startswith("dr"):
            asm += "mov %%%s,%%%s;" \
                "cmp $0x%x,%%%s;" % (reg, t, imm, t)
        elif reg.startswith("st"):
            l = get_addr(size, True)
            asm += gen_reg2mem(reg, "0x%x" % l[0], size).asm
            for j in range(len(l)):
                asm += "cmp $0x%x,0x%x;" % (imm, l[j])
        elif reg == "xcr0":
            l = random.randint(0, 0xffffffff)
            asm += "xgetbv;" \
                    "cmp $0x%x,%%edx;" \
                    "jne forward_%.8x;" \
                    "cmp $0x%x,%%eax;" \
                    "forward_%.8x:" % (imm >> 32, l, imm % 0xffffffff, l)
        else:
            r = resize_reg(reg, size)
            print r
            asm += "cmp $0x%x,%%%s;" % (imm, r)
    else:
        asm += "cmp $0x%x,%s;" % (imm,src)
    g = Gadget(asm = asm, mnemonic = "cmp imm")
    return g


# ===-------------------------------------------------------------------===
# Generate gadget that mov from mem addr1 to mme addr2 via eax
# ===-------------------------------------------------------------------===
def gen_store_mem(src, dest):
    global in_to_reg
    global out_to_reg
    global feistel_r
    global feistel_in
    global feistel_out
    t = "ecx" if any(x in src for x in ["eax", "ax", "ah", "al"]) or \
            any(x in dest for x in ["eax", "ax", "ah", "al"]) else "eax"
    asm = "mov %s,%%%s;" \
        "mov %%%s,%s;" % (src, t, t, dest)
    kill = []
    define = [dest]
    use = []
    use__ = []
    to_reg = in_to_reg.copy()
    to_reg.update(out_to_reg)
    if src in to_reg:
        use__ += [src]
        for r in to_reg[src]:
            use__ += [Register(r.upper())]
    else:
        use += [src]
    if dest in to_reg:
        for r in to_reg[dest]:
            use__ += [Register(r.upper())]
    kill += [Register(t.upper())]
    g = Gadget(asm = asm, mnemonic = "mem2mem", define = define, \
            kill = kill, use = use, use__ = use__)
    return g


# ===-------------------------------------------------------------------===
# Generate gadget to compare a reg with a mem location
# ===-------------------------------------------------------------------===
def gen_cmp_reg2mem(reg, mem, t = "eax", size = 4):
    kill = []
    if reg in ["eflags", "eip", "ip", "mxcsr"] or \
            reg.startswith("cr") or \
            reg.startswith("dr"):
        kill = [Register(t.upper())]
    use = [Register(reg.upper()), mem]
    define = []
    if reg == "xcr0":
        kill += [Register("EAX"), Register("EDX")]
    asm = ""
    if reg == "eflags":
        asm += "pushf;" \
            "pop %%%s;" \
            "cmpl %%%s,%s;" % (t, t, mem)
    elif reg in ["eip", "ip"]:
        asm += gen_get_eip(t)
        asm += "cmpl %%%s,%s;" % (t, mem)
    elif reg == "mxcsr":
        m = get_addr(4, True)[0]
        asm += "ldmxcsr %s;" \
                "mov %s,%%%s;" \
                "cmp %%%s,%s;"% (m, m, t, t, mem)
    elif reg.startswith("cr") or reg.startswith("dr"):
        asm += "mov %%%s,%%%s;" \
            "cmp %%%s,%s;" % (reg, t, t, mem)
    elif reg.startswith("st"):
        if reg == "st(0)":
            asm += "fcom %s;" % mem
        else:
            asm += "fxch %%%s;" \
                "fcom %s;" \
                "fxch %%%s;" % (reg, mem, reg)
    elif reg == "xcr0":
        l = random.randint(0, 0xffffffff)
        asm += "xgetbv;" \
                "cmp %%eax,%s;" \
                "jne forward_%.8x;" \
                "cmp %%edx,%s+0x20;" \
                "forward_%.8x:" % (mem, l, mem, l)
    else:
        r = resize_reg(reg, size)
        asm += "cmp %%%s,%s;" % (r, mem)
    g = Gadget(asm = asm, mnemonic = "cmp", define = define, \
            kill = kill, use = use)
    return g


# ===-------------------------------------------------------------------===
# Generate gadget to compare 2 memory locations
# NOTE: Though involves ``size'' as a param, this function currently only can
# generate correct code for 4 bytes memory locations
# ===-------------------------------------------------------------------===
def gen_cmp_mem(src, dest, size = 4):
    l = []
    t = "ecx" if any(x in src for x in ["eax", "ax", "ah", "al"]) or \
            any(x in dest for x in ["eax", "ax", "ah", "al"]) else "eax"
    l += [gen_mem2reg(src, t, size)]
    l += [gen_cmp_reg2mem(t, dest)]
    return merge_glist(l, "cmp mems")


# ===-------------------------------------------------------------------===
# Generate gadget that mov from mem src to mem dest only if dest != src
# ===-------------------------------------------------------------------===
def gen_store_change_mem(src, dest, mnemonic=""):
    l = random.randint(0, 0xffffffff)
    g_ = [gen_cmp_mem(dest, src)]
    asm = "je forward_%.8x;" % l
    g_ += [Gadget(asm = asm, mnemonic = "")]
    g_ += [gen_store_mem(src, dest)]
    asm = "forward_%.8x:" % l
    g_ += [Gadget(asm = asm, mnemonic = "")]
    g = merge_glist(g_, mnemonic)
    return g

# ===-------------------------------------------------------------------===
# Generate gadget to store current flags to memory
# ===-------------------------------------------------------------------===
def gen_store_eflags(dest):
    asm = "pushf; " \
        "pop %s;" % dest
    g = Gadget(asm = asm, mnemonic = "store flags")      
    return g 


# ===-------------------------------------------------------------------===
# Generate gadget to store immediate value to 32-bit memory
# ===-------------------------------------------------------------------===
def gen_imm2mem(imm, dest):
    asm = "movl $0x%.8x,%s;" % (imm, dest)
    define = [dest]
    use = []
    kill = []    
    g = Gadget(asm = asm, mnemonic = "copy imm", define = define, \
            kill = kill, use = use)
    return g 


# ===-------------------------------------------------------------------===
# Generate gadget to copy from src reg to mem dest
# ===-------------------------------------------------------------------===
def gen_reg2mem(reg, mem, size = 4):
    global in_to_reg
    global out_to_reg
    global feistel_in
    global feistel_out
    define = []
    kill = []
    use = []
    use__ = []
    to_reg = in_to_reg.copy()
    to_reg.update(out_to_reg)
    if in_dict(reg, to_reg) and int(mem, 16) in feistel_in + feistel_out:
        use__ += [Register(reg.upper())]
    else:
        use += [Register(reg.upper())]
        define += [mem]        
    asm = ""
    if reg == "eflags":
        asm += "pushf;" \
            "pop %s;" % mem
    elif reg in ["eip", "ip"]:
        asm += gen_get_eip("eax")
        asm += "mov %%eax,%s;" % mem
    elif reg == "mxcsr":
        asm += "ldmxcsr %s;" % mem
    elif reg.startswith("cr") or reg.startswith("dr"):
        asm += "mov %%%s,%%eax;" \
            "mov %%eax,%s;" % (reg, mem)
    elif reg.startswith("st"):
        use += [Register("CR0")]
        if reg == "st(0)":
            asm += "fstpt %s;" % mem
        else:
            asm += "fxch %%%s;" \
                "fstpt %s;" \
                "fxch %%%s;" % (reg, mem, reg)
    elif reg == "xcr0":
        asm += "xgetbv;" \
            "mov %%edx,%s;" \
            "mov %%eax,%s+0x4;" % (mem, mem)
    else:
        op = size2mov(size, reg)
        r = resize_reg(reg, size)
        asm += "%s %%%s,%s;" % (op, r, mem)
    if asm == "":
        return None
    else:
        g = Gadget(asm = asm, mnemonic = "reg2mem", define = define, \
                kill = kill, use = use, use__ = use__) 
        return g 


# ===-------------------------------------------------------------------===
# Generate gadget to copy from mem src to dest reg
# ===-------------------------------------------------------------------===
def gen_mem2reg(mem, reg, size = 4):
    global feistel_in
    global feistel_out
    use = [mem]
    use__ = []
    define = [Register(reg.upper())]
    kill = []
    to_reg = in_to_reg.copy()
    to_reg.update(out_to_reg)
    if in_dict(mem, to_reg):
        for r in to_reg[mem]:
            use__ += [Register(r.upper())]
    asm = ""
    if reg == "eflags":
        asm += "andl $0xad5,%s;" \
            "push %s;" \
            "popf;" % (mem, mem)
    elif reg in ["eip", "ip", "cs", "tr"]:
        asm = ""
    elif reg == "mxcsr":
        asm += "ldmxcsr %s;" % mem
    elif reg.startswith("cr") or reg.startswith("dr"):
        if reg == "cr0":
            asm += "mov %s,%%eax;" \
                    "orl $0x80000001,%%eax;" \
                    "and $0xc005003f,%%eax;" \
                    "mov %%eax,%%%s;" % (mem, reg)
        else:
            asm += "mov %s,%%eax;" \
                    "mov %%eax,%%%s;" % (mem, reg)
    elif reg.startswith("st"):
        use += [Register("CR0")]
        define += [Register("ST(0)")]
        if reg == "st(0)":
            asm += "fldt %s;" % mem
        else:
            asm += "fxch %%%s;" \
                "fldt %s;" \
                "fxch %%%s;" % (reg, mem, reg)
    elif reg == "xcr0":
        asm += "mov %s,%%edx;" \
            "mov %s+0x4,%%eax;" \
            "xsetbv;" % (mem, mem)
    else:
        op = size2mov(size, reg)
        r = resize_reg(reg, size)
        asm += "%s %s,%%%s;" % (op, mem, r)         
    if asm == "":
        return None
    else:
        g = Gadget(asm = asm, mnemonic = "mem2reg", define = define,\
                kill = kill, use = use, use__ = use__)
        return g 


# ===-------------------------------------------------------------------===
# Generate gadget that xor src1 to src2, and copy the result(in src2) to dest
# src1 is a block in the Feistel L block, src2 is a new output
# Usually src1 and dest are mem locations while src2 can be either mem or reg 
# NOTE: Xed info is not enough for this funcion, since it cannot tell registers
# that cannot be XORed directly.
# ===-------------------------------------------------------------------===
def gen_feistel_cipher(src1, src2, dest, size = 4, clean = False):
    global l_insn
    global in_to_reg
    feistel = []
    
    t = ""
    if src2.startswith("mm"):
        t = "mm0" if not (src2 == "mm0") else "mm1"
    elif src2.startswith("xmm"):
        t = "xmm0" if not (src2 == "xmm0") else "xmm1"
    elif size <= 4:
        a = ["eax", "ax", "al", "ah"]
        if any(x in src1 for x in a) or any(x in src2 for x in a):
            t = "ecx"
        else:
            t = "eax"
    elif size in range(9,17) or (size in range (5, 9) and src2.startswith("xmm")):
        t = "xmm0" if not (src2 == "xmm0") else "xmm1"        
    elif size in range(5, 9) :
        t = "mm0" if not (src2 == "mm0") else "mm1"
    else:
        assert 0
        
    if DEBUG >= 3:
        print "dest = %s, size = %d, src2 = %s, t = %s" % (dest, size, src2, t)
    g1 = gen_mem2reg(src1, t, size)    
    g3 = gen_reg2mem(t, dest, size)
    asm2 = ""
    define = []
    kill = []
    use = []
    use__ = []
    if src2 in reg_map.values():
        use += [Register(src2.upper())]
    else:
        use += [src2]
        if src2 in in_to_reg:
            for r in in_to_reg[src2]:
                use__ += [Register(r.upper())]
    
    if src2 == "eflags":
        r = "0x%x" % get_addr(4, True)[0]
        asm2 += gen_store_eflags(r).asm
        asm2 += "xor %s,%%eax;" % r
#         src2 = r
    elif src2 in ["eip", "ip"]:
        # Made the following assumptions: 
        # 1 - we want the eip value immediately after the tested insn
        # 2 - this gadget locates after that instruction
        r = random.randint(0, 0xffffffff)
        asm2 += gen_get_eip("ecx", r)
        asm2 += "sub $(forward_%.8x - forward_%.8x),%%ecx;" \
            "xor %%ecx,%%eax;" % (r, l_insn)
    elif src2 in ["cs", "ds", "es", "ss", "fs", "gs"] or src2.startswith("cr") \
        or src2.startswith("dr"):
        asm2 += "mov %%%s,%%ecx; xor %%ecx,%%eax;" % src2
        if clean:
            g3.asm += "mov $0x0,%%ecx; mov %%ecx,%%%s;" % src2
        kill += [Register("ECX")]                            
    elif src2 == "mxcsr":
        d = "0x%x" % get_addr(4, True)[0]
        asm2 += "stmxcsr %s;" \
            "xor %s,%%%s;" % (d, d, t)
    elif src2 == "xcr0":
        d = "0x%x" % get_addr(8, True)[0]
        asm2 += gen_reg2mem(src2, d, 8).asm
        kill += [Register("EAX"), Register("EDX")]
        asm2 += "pxor %s,%%%s;" % (d, t)

    else:
        m = size2mov(size, src2)
        x = size2xor(size, src2)
        r = resize_reg(t, size)
        format_str = "%s %%%s,%%%s;" if src2 in reg_map.values() else "%s %s,%%%s;"
        asm2 += format_str % (x, src2, r)
        if clean:
            if src2 in reg_map.values():
                g3.asm += "%s %%%s,%%%s;" % (x, src2, src2)
            else:
                l = random.randint(0, 0xffffffff)
                g3 = merge_glist([g3, gen_cmp_imm(src2, 0, t)])
                g3.asm += "je forward_%.8x;" % l
                g3.asm += "%s %%%s,%%%s;"\
                        "%s %%%s,%s;" % (x, r, r, m, r, src2)
                g3.asm += "forward_%.8x:" % l
    g2 = Gadget(asm = asm2, mnemonic = "feistel", define = define, kill= kill, use = use, \
            use__ = use__)
    g = merge_glist([g1, g2, g3])
    g.kill = g.kill | set([Register(t.upper())])
    g.define -= set([Register(t.upper())])
    if src2 in ["eax", "ax", "al", "ah", "eflags"]:
        g.asm = "push %eax; push %ecx;" + g.asm + "pop %ecx; pop %eax;"
        g.kill = g.kill - set([Register("EAX"), Register("ECX")])
    return g


# ===-------------------------------------------------------------------===
# Get the ith explicit operand. i starts from 0.
# Can be either mem or reg. First mem than reg.
# The 2nd return value := whether this operand is memory accessing
# ===-------------------------------------------------------------------===
def get_explicit_op(inst, i):
    count = 0
    op_str = ""
    for i in range(inst.get_noperands()):
        op = inst.get_operand(i)
        name = get_operand_name(op.get_name())
        print "operand: %s" % name
        if is_explicit(op.get_visibility()):
            if count == i:
                print "Find explicit"
                if op.is_register() or op.is_memory_addressing_register():                 
                    print "    reg"
                    (op_str, op_len) = get_reg_op(inst, op, i)
                    if op_str == "" or op_len == 0:
                        return (None, 0, False)
                    else:
                        return (op_str, op_len, False)
                elif name in ["XED_OPERAND_AGEN", "XED_OPERAND_MEM0", "XED_OPERAND_MEM1"]:
                    print "    mem"
                    (op_str, op_len, _) = get_mem_op(inst, op, i)
                    if op_str == None:
                        return (None, 0, False)
                    else:
                        return (op_str, op_len, True)
            else:
                count = count + 1
                
    return (None, 0, False)            
        

# ===-------------------------------------------------------------------===
# If the `i`-th operand is the j-th memory operand, return j
# UNTESTED
# ===-------------------------------------------------------------------===
def get_nmemop(inst, i):
    count = 0
    for e in range(0, i+1):
        op = inst.get_operand(e)
        name = get_operand_name(op.get_name())
        if name in ["XED_OPERAND_AGEN", "XED_OPERAND_MEM0", "XED_OPERAND_MEM1"]:
            count += 1
    return (count - 1)
           

# ===-------------------------------------------------------------------===
# Handle an memory accessing operand for feistel aggregated PokeEMU
# NOTE: Since an GAS instruction can have at most 1 memory accessing, use index-
# 0 to get seg, base, index, scale and offset (disp)
# ===-------------------------------------------------------------------===
def get_mem_op(inst, op, i, d = 0):
    global retseg
    reglist = []
    seg = inst.get_seg_reg(0)                
    offset = 0
    disp_len = inst.get_memory_displacement_width(0)
    if disp_len:        
        offset = inst.get_memory_displacement(0)
    base = inst.get_base_reg(0)        
    indx = inst.get_index_reg(0)
    scale = inst.get_scale(0)
    iclass = get_iclass(inst.get_iclass())
    op_str = ""
    if (reg_map[seg] != "" and reg_map[seg] != "ds") or \
        (reg_map[seg] == "ds" and iclass == "XED_ICLASS_XLAT"):
        op_str += "%%%s:" % reg_map[seg]
    if (reg_map[seg] == "fs"):
        retseg = "gs"
    if disp_len != 0 or \
    not (reg_map[seg] != "" and reg_map[seg] != "ds"):  #displacement bits
        op_str += "0x%x" % (offset + d)
    if reg_map[seg] != "":
        reglist += [reg_map[seg]]
    if base != 0:
        op_str += "(%%%s" % reg_map[base]
        if reg_map[base] != "":
            reglist += [reg_map[base]]
        if reg_map[indx] != "" and iclass != "XED_ICLASS_XLAT":
            op_str += ",%%%s" % reg_map[indx]
            reglist += [reg_map[indx]]
        if scale != 0 and iclass != "XED_ICLASS_XLAT":
            op_str += ",%d" % scale
        op_str += ")"    
#     op_len = inst.get_operand_length_bits(i)
    op_len = inst.get_operand_length(i)
    return (op_str, op_len, set(reglist))    


def handle_mem_read(inst, op, i, isInit = False):
    global l_restore
    global in_to_reg
    global init_r
    global feistel_r
    global feistel_r_bak
    global feistel_in
    global count_l
    global count_r    
    setinput = []
    feistel = [] 
    restore = []
    backup = []     
    
    opcode = get_category(inst.get_category())
    (trg, _, _) = get_explicit_op(inst, 0)
    if opcode == "XED_CATEGORY_POP":
        print trg
        return ([], [], [], [])
    (op_str, op_len, s) = get_mem_op(inst, op, i)
    in_to_reg[op_str] = s

    if DEBUG >= 2:
        print "handle_mem_read    %s, %d" % (op_str, op_len)    
    if inst.is_mem_read(0):
        f = get_addr(op_len)
        r_bak = get_addr(op_len)
        bak = get_addr(op_len)
        assert(len(f) == len(r_bak))
        for idx, val in enumerate(f):
            (op_str, _, _) = get_mem_op(inst, op, i, (idx * 4))
            if isInit:             
                feistel_r += [val]
                feistel_r_bak += [r_bak[idx]]
                feistel_in += [bak[idx]]
                r = "0x%x" % feistel_r[count_r]                
                init_r += [gen_store_mem(op_str, r)]
            src = "0x%x" % feistel_r[count_r]
            op_bak = "0x%x" % feistel_in[count_r]

            if not op_str in l_restore:
                setinput += [gen_store_change_mem(src, op_str, "setinput")]
                l_restore += [op_str]
                backup += [gen_store_mem(op_str, op_bak)]
                restore_ = []
                restore += [gen_store_change_mem(op_bak, op_str, "restore inputs")]

            count_r += 1  
    return (backup, setinput, feistel, restore)
    
    
def handle_mem_write(inst, op, i, isInit = False):
    global l_restore
    global out_to_reg
    global init_r
    global init_l
    global feistel_l
    global feistel_r
    global feistel_r_bak
    global feistel_in
    global feistel_out
    global count_l
    global count_r    
    setinput = []
    feistel = []      
    restore = []
    backup = []
    
    (op_str, op_len, s) = get_mem_op(inst, op, i)
    out_to_reg[op_str] = s
    if DEBUG >= 2:
        print "handle_mem_write    %s, %d" % (op_str, op_len)
    if inst.is_mem_written(0):
        if isInit:
            l = get_addr(op_len)
            bak = get_addr(op_len)
            feistel_l += l
            feistel_out += bak 
            for val in l:
                init_l += [gen_imm2mem(gen_seed(), "0x%x" % val)]                                
        r = int(math.ceil(float(op_len)/4))
        print "Need %d mem blocks in total" % r
        if DEBUG >= 2:
            d = count_l + r - len(feistel_r)
            if d > 0:
                print "Need %d more R blocks" % d
        while count_l + r > len(feistel_r):
            feistel_r += get_addr()
            feistel_r_bak += get_addr()
            feistel_in += get_addr()        
        for j in range(r):
            src1 = "0x%x" % feistel_l[count_l + j]
            (src2, _, _) = get_mem_op(inst, op, i, j * 4)
            op_bak = "0x%x" % feistel_out[count_l + j]
            dest = "0x%x" % feistel_r[count_l + j]        
            feistel += [gen_feistel_cipher(src1, src2, dest, 4)]

            if not op_str in l_restore: 
                l_restore += [op_str]
                backup += [gen_store_mem(src2, op_bak)]
                restore_ = []
                restore += [gen_store_change_mem(op_bak, src2, "restore inputs")]
        count_l += r
        
    return (backup, setinput, feistel, restore)


# ===-------------------------------------------------------------------===
# Handle an register operand for feistel aggregated PokeEMU
# ===-------------------------------------------------------------------===
def get_reg_op(inst, op, i):  
    reg = inst.get_reg(op.get_name())
    reg_str = reg_map[reg]
    reg_len = inst.get_operand_length(i)
    if reg_str == "gdtr":
        reg_str = ""
    return (reg_str, reg_len)


def handle_reg_read(inst, op, i, isInit = False):
    global l_restore
    global in_to_reg
    global out_to_reg
    global init_r
    global feistel_r
    global feistel_r_bak
    global feistel_in
    global count_l
    global count_r    
    setinput = []
    feistel = []  
    restore = []
    backup = []
    
    iclass = get_iclass(inst.get_iclass())
    if iclass == "XED_ICLASS_LTR":
        return ([],[],[],[])
    (reg_str, reg_len) = get_reg_op(inst, op, i)
    print "reg_str: %s" % reg_str
    if reg_str == "" or reg_len == 0:
        return ([], [], [], [])
    in_to_reg[reg_str] = reg_str 
     
    if op.is_read_only() or op.is_read_and_written(): 
        if isInit:
            f = get_addr(reg_len)
            r_bak = get_addr(reg_len)
            bak = get_addr(reg_len)
            assert(len(f) == len(r_bak))
            if DEBUG >= 2:
                print "reg_len:%d    Get %d blocks" % (reg_len, len(f))            
            for idx, val in enumerate(f):
                feistel_r += [val]
                feistel_r_bak += [r_bak[idx]]
                feistel_in += [bak[idx]]                
            r = "0x%x" % feistel_r[count_r]
            g = gen_reg2mem(reg_str, r, reg_len)
            to_reg = in_to_reg.copy()
            to_reg.update(out_to_reg)
            if reg_str in to_reg:
                g.use__ |= set([Register(reg_str.upper())])
                g.use -= set([Register(reg_str.upper())])
            init_r += [g] 
        size = int(math.ceil(float(reg_len) / 4))                        
        src = "0x%x" % feistel_r[count_r]
        print "src = %s" % src
        reg_bak = "0x%x" % feistel_in[count_r]
        setinput += [gen_mem2reg(src, reg_str, reg_len)]

        if not reg_str in l_restore:
            l_restore += [reg_str]
            if reg_str in ["cs", "ds", "es", "fs", "gs", "ss"]:
                backup += [gen_reg2mem(reg_str, reg_bak, reg_len)]
            else:
                backup += [gen_reg2mem(resize_reg(reg_str), reg_bak)]
            restore_ = []
            t = "ecx" if reg_str in ["eax", "ax", "ah", "al"] else "eax"
            if reg_str in ["cs", "ds", "es", "fs", "gs", "ss"]:
                restore += [gen_mem2reg(reg_bak, reg_str, reg_len)]
            else:
                restore_ += [gen_mem2reg(reg_bak, resize_reg(reg_str))]
            g = merge_glist(remove_none(restore_), "restore inputs")
            if reg_str == "eflags":
                g.asm = "push %%%s;" % t + g.asm.split("//")[0] + "pop %%%s; //restore inputs" % t
                g.kill -= set([Register(t.upper())])
            restore += [g]

        count_r += size
    else:
        print "No read"

    return (backup, setinput, feistel, restore)                               
         
         
def handle_reg_write(inst, op, i, isInit = False):
    global l_restore
    global out_to_reg
    global init_r
    global init_l
    global feistel_l
    global feistel_r
    global feistel_r_bak
    global feistel_in
    global feistel_out
    global count_l
    global count_r    
    setinput = []
    feistel = []  
    restore = []
    backup = []
    
    (reg_str, reg_len) = get_reg_op(inst, op, i)
    if reg_str == "" or reg_len == 0:
        return ([], [], [], [])
    out_to_reg[reg_str] = reg_str
            
    if op.is_written_only() or op.is_read_and_written():
        if op.is_written_only():
            print "reg_str: %s(W)" %reg_str
        elif op.is_read_and_written():
            print "reg_str: %s(RW)" %reg_str
        if isInit:
            l = get_addr(reg_len)
            bak = get_addr(reg_len)
            feistel_l += l
            feistel_out += bak 
            for val in l:
                init_l += [gen_imm2mem(gen_seed(), "0x%x" % val)]                  
        src1 = "0x%x" % feistel_l[count_l]
        src2 = reg_str
        print "count_r = %d, count_l = %d, reg_len = %d" % (count_r, count_l, reg_len)
        r = int(math.ceil(float(reg_len) / 4))
        if DEBUG >= 2:
            d = count_l + r - len(feistel_r)
            if d > 0:                
                print "Need %d more R blocks" % d
        while count_l + r > len(feistel_r):
            feistel_r += get_addr()
            feistel_r_bak += get_addr()
            feistel_in += get_addr()
        dest = "0x%x" % feistel_r[count_l]
        if reg_str.startswith("st"):
            l = get_addr(reg_len, True)            
            feistel_ = []
            feistel_ += [gen_reg2mem(reg_str, "0x%x" % l[0], reg_len)]
            for j in range(len(l)):
                src1 = "0x%x" % feistel_l[count_l + j]
                dest = "0x%x" % feistel_r[count_l + j]
                src2 = "0x%x" % l[j]                
                feistel_ += [gen_feistel_cipher(src1, src2, "0x%x" % feistel_r[count_l + j], 4)]
            feistel += [merge_glist(feistel_, "feistel fpu")]
        else:
            feistel += [gen_feistel_cipher(src1, src2, dest, reg_len)]
        reg_bak = "0x%x" % feistel_out[count_l]

        if not reg_str in l_restore:            
            if reg_str in ["cs", "ds", "es", "fs", "gs", "ss"]:
                backup += [gen_reg2mem(reg_str, reg_bak, reg_len)]
            else:
                backup += [gen_reg2mem(resize_reg(reg_str), reg_bak)]
            restore_ = []
            t = "ecx" if reg_str in ["eax", "ax", "ah", "al"] else "eax" 
            if reg_str in ["cs", "ds", "es", "fs", "gs", "ss"]:
                restore += [gen_mem2reg(reg_bak, reg_str, reg_len)]
            else:
                restore_ += [gen_mem2reg(reg_bak, resize_reg(reg_str))]
            g = merge_glist(remove_none(restore_), "restore outputs")
            if reg_str == "eflags":
                g.asm = "push %%%s;" % t + g.asm.split("//")[0] + "pop %%%s; //restore outputs" % t
                g.kill -= set([Register(t.upper())])
            restore += [g]
        count_l += r
        
    return (backup, setinput, feistel, restore)         


# ===-------------------------------------------------------------------===
# For simple aggregating mode only. copy ouputs of an insn to somewhere else   
# ===-------------------------------------------------------------------===
def copy_mem_write(inst, op, i, isInit = False):
    out = []    
    (op_str, op_len, _) = get_mem_op(inst, op, i)
    if inst.is_mem_written(0):
        for val in get_addr(op_len, True):
            dest = "0x%x" % val
            out += [gen_store_mem(op_str, dest)] 
    return ([], [], out, [])


def copy_reg_write(inst, op, i, isInit = False):
    out = []
    (reg_str, reg_len) = get_reg_op(inst, op, i)
    if reg_str == "" or reg_len == 0:
        return ([], [], [], [])
        
    if op.is_written_only() or op.is_read_and_written():
        dest = "0x%x" % get_addr(reg_len, True)[0]
        out += [gen_reg2mem(reg_str, dest, reg_len)]
    
    return ([], [], out, [])     

# ===-------------------------------------------------------------------===
# For each mem/reg operand, run function <hanlde_XXX> to handle it 
# ===-------------------------------------------------------------------===
def handle_op(inst, handle_mem, handle_reg, isInit):    
    setinput = []
    output = []
    restore = []
    backup = []
            
    for i in range(inst.get_noperands()):
        op = inst.get_operand(i)
        if op.is_register() or op.is_memory_addressing_register():  
            name = get_operand_name(op.get_name())
            (reg, _) = get_reg_op(inst, op, i)
            if DEBUG >= 2:
                print "* reg op    %s" % name                    
            (b, s, f, r) = handle_reg(inst, op, i, isInit)
            setinput += s
            if reg in ["eflags"]:
                output = f + output
            else:
                output += f
            restore += r
            backup += b
             
    for i in range(inst.get_noperands()):
        op = inst.get_operand(i)         
        name = get_operand_name(op.get_name())
        if name in ["XED_OPERAND_AGEN", "XED_OPERAND_MEM0", "XED_OPERAND_MEM1"]:
            if DEBUG >= 2:
                print "* mem op    %s" % name
            (b, s, f, r) = handle_mem(inst, op, i, isInit)
            setinput += s
            output += f
            restore += r
            backup += b
 
    return (remove_none(backup), remove_none(setinput), remove_none(output), remove_none(restore))


# ===-------------------------------------------------------------------===
# check whether 2 registers are in fact the same one
# ===-------------------------------------------------------------------===
def is_equal_reg(r1, r2):
    def equal(e1, e2, l):
        if e1 in l and e2 in l and not (e1[-1] == 'L' and e2[-1] == 'H') and \
                not (e1[-1] == 'H' and e2[-1] == 'L'):
            return True
    reglist = [["EAX", "AX", "AL", "AH"], ["EBX", "BX", "BL", "BH"], \
            ["ECX", "CX", "CL", "CH"], ["EDX", "DX", "DL", "DH"]]
    for l in reglist:
        if equal(r1, r2, l):
            return True        


class Register:
    def __init__(self, name, value = None, size = 32):
        self.name = name
        self.value = value
        self.size = size

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __hash__(self):
        if self.name in ["EAX", "AX", "AL", "AH"]:
            return hash("EAX")
        elif self.name in ["EBX", "BX", "BL", "BH"]:
            return hash("EBX")
        elif self.name in ["ECX", "CX", "CL", "CH"]:
            return hash("ECX")
        elif self.name in ["EDX", "DX", "DL", "DH"]:
            return hash("EDX")
        return hash(self.name)

    def __eq__(lhs, rhs):
        return (lhs.name == rhs.name) or \
                (is_equal_reg(lhs.name, rhs.name))

    def gen_gadget(self, snapshot):
        return Gadget.gen_set_reg(self, snapshot)
        
    def in_snapshot(self, snapshot):
        return in_snapshot_reg(self.name, snapshot)
    
    def gen_revert_gadget(self, snapshot):
        self.value = self.in_snapshot(snapshot)
        return self.gen_gadget(snapshot)    


class SegmentRegister(Register):
    def __init__(self, name, value = None):
        Register.__init__(self, name, value, size = 16)

    def gen_gadget(self, snapshot):
        return Gadget.gen_set_sreg(self, snapshot)
            
    def in_snapshot(self, snapshot):
        return in_snapshot_sreg(self.name, snapshot)
    
    def gen_revert_gadget(self, snapshot):
        self.value = self.in_snapshot(snapshot)
        return self.gen_gadget(snapshot)

class ControlRegister(Register):
    def __init__(self, name, value = None):
        Register.__init__(self, name, value)

    def in_snapshot(self, snapshot):
        return in_snapshot_creg(self.name, snapshot)

    def gen_gadget(self, snapshot):
        return Gadget.gen_set_creg(self, snapshot)
    
    def gen_revert_gadget(self, snapshot):
        self.value = self.in_snapshot(snapshot)
        return self.gen_gadget(snapshot)        


class DebugRegister(Register):
    def __init__(self, name, value = None):
        Register.__init__(self, name, value)
        assert 0


class Memory:
    def __init__(self, address, value = None, symbol = None):
        self.address = address
        self.value = value
        self.symbol = symbol
    
    def __str__(self):
        return "%.8x" % self.address

    def __repr__(self):
        return "%.8x" % self.address

    def __hash__(self):
        return self.address

    def __eq__(lhs, rhs):
        return lhs.address == rhs.address

    def gen_gadget(self, snapshot):
        return Gadget.gen_set_mem(self, snapshot)

    def in_snapshot(self, snapshot):
        return in_snapshot_mem((self.address, 1), snapshot)

    def gen_revert_gadget(self, snapshot):
        self.value = self.in_snapshot(snapshot)
        return Gadget.gen_set_mem(self, snapshot, retseg)


# ===-----------------------------------------------------------------------===
# Snippets of code for setting the state of the CPU
# ===-----------------------------------------------------------------------===
class Gadget:
    def __init__(self, asm, mnemonic, define = None, kill = None, use = None, use__ = None):
        self.asm = asm
        self.mnemonic = mnemonic

        if define is None: define = set()
        self.define = set(define)
        if kill is None: kill = set()
        self.kill = set(kill)
        if use is None: use = set()
        self.use = set(use)
        if use__ is None: use__ = set()
        self.use__ = set(use__)

    def __str__(self):
        r = "Gadget '%s'\n" % (self.mnemonic)
        r += "   [*] asm:    %s\n" % (self.asm)
        r += "   [*] define: %s\n" % (", ".join([str(d) for d in self.define]))
        r += "   [*] kill:   %s\n" % (", ".join([str(k) for k in self.kill]))
        r += "   [*] use:    %s\n" % (", ".join([str(u) for u in self.use]))
        r += "   [*] use-after-define:    %s\n" % (", ".join([str(u) for u in self.use__]))
        return r

    # ===-------------------------------------------------------------------===
    #  
    # ===-------------------------------------------------------------------===
    def __add__(self, other):
        asm = self.asm.split("//")[0] + other.asm.split("//")[0]
        mnemonic = self.mnemonic + "-" + other.mnemonic
        define = self.define | other.define
        kill = self.kill | other.kill
        use = self.use | other.use
        use__ = self.use__ | other.use__

        # Remove cycles
        define -= other.kill
        use -= other.kill
        use -= self.kill
        use -= (self.define & other.use)
        kill -= (self.kill & other.define)
        
        g = Gadget(asm, mnemonic, define, kill, use, use__)
        return g

    def __repr__(self):
        return self.mnemonic

    # ===-------------------------------------------------------------------===
    # Return true (= g1 depend on g0 / add edge (g0, g1)) if any of the followings is true:
    # * g1 defines what g0 kills 
    # * g0 uses what g1 defines
    # ===-------------------------------------------------------------------===
    def depend(g1, g0):
        return (g1.define & g0.kill) or \
            (g0.use & g1.define or "*" in g1.define) or \
            (g0.use & g1.kill) or \
            (g0.define & g1.use__) or \
            (Register("EFLAGS") in g0.use and not Register("EFLAGS") in g1.use) or \
            (("pde" in g0.define or "pte" in g0.define) and Register("EFLAGS") in g1.define)

    # ===-------------------------------------------------------------------===
    # Generate a gadget to set a register
    # ===-------------------------------------------------------------------===
    @staticmethod
    def gen_set_reg(reg, snapshot):
        asm = "nop; // %s" % (reg.name.lower())
        define, kill, use = [reg], [], []

        if reg.name == "EFLAGS":
            asm = "nop; push $0x%.8x; nop; popf; // eflags" % (reg.value)
            use += ["stack*"]
        elif reg.name == "EIP":
            pass
        else:
            asm = "movl $0x%.8x,%%%s; // %s" % (reg.value, reg.name.lower(), 
                                                reg.name.lower())

        return [Gadget(asm = asm, mnemonic = reg.name.lower(), define = define,
                       kill = kill, use = use)]


    @staticmethod
    def gen_set_sreg(reg, snapshot):
        asm = "nop; // %s" % (reg.name.lower())
        define, kill, use = [reg], [], []
            
        print "gen_set_sreg: %s" % reg.name
        if reg.name == "CS":
            r = random.randint(0, 0xffffffff)
            # Generate a long jump (we set the address at runtime with another
            # gadget)
            asm0 = "ljmp $0x%.4x,$0x00000000; " \
                "target_%.8x: // cs" % (reg.value, r)

            # Patch the target of the long jump (but before compute the absolute
            # address)
            asm1 = "lea target_%.8x, %%ebx; " \
                "lea forward_%.8x, %%eax; " \
                "sub %%eax, %%ebx; " \
                "call forward_%.8x; " \
                "forward_%.8x: " \
                "pop %%eax;" \
                "add %%eax, %%ebx; " \
                "mov %%ebx, -6(%%ebx); // patch ljmp target" % (r, r, r, r)

            g0 = Gadget(asm = asm0, mnemonic = reg.name.lower(), 
#                         define = define + ["patch_ljmp_target", "*"],
                        define = define + ["patch_ljmp_target"], 
                        kill = kill, use = [])

            g1 = Gadget(asm = asm1, mnemonic = "patch_ljmp_target", 
                        kill = [Register("EAX"), Register("EBX"), 
                                Register("EFLAGS")], 
                        use = ["mem*", "stack*", "patch_ljmp_target"],
                        define = [])

            return [g1, g0]

        else:
            asm = "mov $0x%.4x,%%ax; mov %%ax,%%%s; // %s" % \
                (reg.value, reg.name.lower(), reg.name.lower())
            kill = [Register("EAX")]

            if reg.name == "DS":
                define += ["mem*"]
                
            if reg.name == "SS":
                define += ["stack*"]

            return [Gadget(asm = asm, mnemonic = reg.name.lower(), 
                           define = define, kill = kill, use = use)]


    @staticmethod
    def gen_set_creg(reg, snapshot):
        global next_addr
        global start_addr
        global end_addr
        global PG        
        define, kill, use = [reg], [Register("EAX")], []
        if reg.name.lower() == "cr0":
            if not reg.value & 0x80000000:
                print "Paging turned off. Should use unextended range only."
                if PG != 0:
                    PG = 0
                    flip_addrs()
        asm = "mov $0x%.8x, %%eax; mov %%eax,%%%s; // %s" % \
            (reg.value, reg.name.lower(), reg.name.lower())
        print define
        return [Gadget(asm = asm, mnemonic = reg.name.lower(), define = define,
                       kill = kill, use = use)]


    @staticmethod
    def gen_set_dreg(reg, value, snapshot):
        assert 0, "Not implemented yet"


    # ===-------------------------------------------------------------------===
    # Generate a gadget to set the content of a memory location
    # ===-------------------------------------------------------------------===
    @staticmethod
    def gen_set_mem(mem, snapshot, seg = None):
        gadgets = []
        data = mem.value
        addr = mem.address
        sym = mem.symbol
        invlpg = ""
        for i in range(len(data)):
            define = [mem]
            use = ["mem*", "pde", "pte", "gdt"]
            kill = []

            if sym: sym_ = sym
            else: sym_ = hex(addr)

            if sym.startswith("PDE_") or sym.startswith("PTE_"):
                entry = int(sym.split("_")[1])
                page = entry << 22
                invlpg = " mov %cr3,%eax; mov %eax,%cr3;"
                kill += [Register("EAX")]
                if sym.startswith("PDE_"):
                    define += ["pde"]
                    use = ["mem*"]
                else:
                    define += ["pte"]
                    use = ["mem*"]
            # elif sym.startswith("PTE_"):
            #     deref4 = lambda x: deref(x, 0, 4)
            #     cr3 = in_snapshot_creg("CR3", snapshot) & 0xfffff000
            #     pde0 = in_snapshot_mem((cr3, 4), snapshot)
            #     pte0 = struct.unpack("I", pde0)[0] & 0xfffff000
            #     print hex(pte0)
            #     j = ((addr - pte0) / 4) << 12
            #     invlpg = " invlpg 0x%x;" % j
            

            if seg is None:
                asm = "movb $0x%.2x,0x%.8x;%s // %s + %d" % \
                        (ord(data[i]), addr + i, invlpg, sym_, i);
            else:
                asm = "movb $0x%.2x,%%%s:(0x%.8x);%s // %s + %d" % \
                        (ord(data[i]), seg, 0x1000000 + addr + i, invlpg, sym_, i);

            mnemonic = "%.8x %s" % (addr + i, sym)

            # If address belongs to the GDT kill the corresponding segment
            # selector
            if isgdt(sym):
                define += ["gdt"]
                use = ["mem*", "pde", "pte"]
                idx = int(sym.split("_")[1])
                sregs = [SegmentRegister(r) for r in \
                             ["DS", "CS", "SS", "ES", "FS", "GS"]]
                for sreg in sregs:
                    sel = sreg.in_snapshot(snapshot) >> 3
                    if sel == idx:
                        kill += [sreg]
            gadgets += [Gadget(asm = asm, mnemonic = mnemonic, define = define,
                               kill = kill, use = use)]

        return gadgets

    
    # ===-------------------------------------------------------------------===
    # Generate a gadget to notify the end of the testcase
    # ===-------------------------------------------------------------------===
    @staticmethod
    def gen_end_testcase():
        r = random.randint(0, 0xffffffff)
        asm = "int $0x20; jmp forward_%.8x;forward_%.8x:" \
            "hlt; // notify the end of the test-case" % \
            (r, r)
        
        return [Gadget(asm = asm, mnemonic = "the end")]
    
    
    # TODO: gen_root doesn't only gen root. 
    # e.g. setinput, backup and restore are not root gadgets
    # Perhaps we need another name for this function
    # ===-------------------------------------------------------------------===
    # Generate a gadget to run the shellocde (i.e., the real testcase)
    # ===-------------------------------------------------------------------===
    @staticmethod
    def gen_root(snapshot, shellcode, count):
        global l_insn
        global l_restore
        global count_l
        global count_r  
        global init_r
        global init_l      
        global feistel_l
        global feistel_r
        global feistel_r_bak
        global count_addr
        
        f = Tempfile()
        f.write(shellcode)
        p = subprocess.Popen(["xxd", "-p", "%s" % f], 
                             stdin=subprocess.PIPE, 
                             stdout=subprocess.PIPE)
        s = p.communicate()[0].rstrip()     
           
        print "%s (%d)" % (s, len(s))
        xed = pyxed.Decoder()
        xed.set_mode(pyxed.XED_MACHINE_MODE_LEGACY_32, pyxed.XED_ADDRESS_WIDTH_32b)
        xed.itext = binascii.unhexlify(s)
    #     xed.runtime_address = 0x10001000
        xed.runtime_address = 0x0
    
        inst = xed.decode()    
        inst_str = inst.dump_intel_format()
        print "%s" % inst_str 
        
        isInit = False
        if count == 1:
            isInit = True                     
        
        #TODO: rewrite resetting code using Xed
        #5 groups of root Gadgets that gen_root will generate from an instruction
        # * = Need Xed         
        set_r = []
        setinput = []   #copy from R block to input*
        backup = []     #backup original input & output of the tested insn for restoring
        backup_r = []     #backup R block
        code = []       #instruction to run and corresponding reset*         
        output = []    # Handle output of the core insn. In feistel mode it compute XOR
        restore = []
        update = []     # Copy R_backup to L blocks
        
        # code
        x = ",".join("0x%.2x" % ord(b) for b in shellcode)
        r = random.randint(0, 0xffffffff)
        l_insn = r
        tc = "jmp forward_%.8x;forward_%.8x: " \
            ".byte %s;// shellcode: %s" % (r, r, x, inst_str) 
        gtc = Gadget(asm = tc, mnemonic = "shellcode")
                
        deref4 = lambda x: deref(x, 0, 4)
        cr0 = in_snapshot_creg("CR0", snapshot)
        cr3 = in_snapshot_creg("CR3", snapshot) & 0xfffff000
        pde0 = in_snapshot_mem((cr3, 4), snapshot)
        print "gen_prologue: pde0 = #%s#\n" % pde0
        pte0 = in_snapshot_mem((deref4(pde0) & 0xfffff000, 4), snapshot)
        pte1022 = in_snapshot_mem((((deref4(pde0) & 0xfffff000) + 1022*4), 4), 
                                  snapshot)
        newpte0 = (deref4(pte0) & 0xfff) | (deref4(pte1022) & 0xfffff000)
        eax_backup = get_addr(4, True)[0]        
        rs = "mov %%eax,0x%.8x; mov $0x%.8x,%%eax; mov %%eax,%%cr0; mov 0x%.8x,%%eax; " \
            "movl $0x%s,0x%.8x; " \
            "movl $0x%.8x,0x%.8x; " \
            "movl $0x0,0x%.8x; // rebase page 0" % \
            (eax_backup, cr0, eax_backup, binascii.hexlify(pde0[::-1]), cr3 ,\
            newpte0, deref4(pde0) & 0xfffff000, eax_backup)
        grs = Gadget(asm = rs, mnemonic = "rebase page 0") 
        
        code += [gtc]
        
        opcode = get_category(inst.get_category())        
        if MODE >= 1 and opcode == "XED_CATEGORY_CALL":
            # Overwritten call target, so that it will jump back to next insn
            (trg, trg_len, isMem) = get_explicit_op(inst, 0)
            if trg is not None and trg_len >= 4:
                l1 = random.randint(0, 0xffffffff)
                l2 = random.randint(0, 0xffffffff)
                print "call target: %s" % trg
                callcode = "jmp forward_%.8x;" \
                    "forward_%.8x:" \
                    "ret;" \
                    "forward_%.8x: " % (l1, l2, l1)
                callcode += ("mov $forward_%.8x,%%eax; mov %%eax,%s;" % (l2, trg)) \
                    if isMem else ("mov $forward_%.8x,%%%s;" %  (l2, trg))
                g_call = Gadget(asm = callcode, mnemonic = "handle call", kill = ["EAX"])
                code = [g_call] + code
        if MODE >=1 and opcode == "XED_CATEGORY_COND_BR":
            nop = ""
            for i in range(0, 128):
                nop += "nop;"
            gnop = Gadget(asm = nop, mnemonic = "nop zone")
            code = [gnop] + code + [gnop]
#         code += [grs]
        if MODE >= 2:
        # Feistel & Feistel looping mode
            # Handle all read operations in 1st round, and then handle write operations
            if DEBUG >= 2:
                print "******************************************************************************"
                print "There are %d ops and %d mem ops" % (inst.get_noperands(), \
                        inst.get_number_of_memory_operands())
                print "==================== READ ===================="
            feistel = []
            (b, s, f, r) = handle_op(inst, handle_mem_read, handle_reg_read, isInit)
            setinput += s
            feistel += f
            restore += r
            backup += b
                
            if DEBUG >=2:
                print "==================== WRITE ===================="        
            (b, s, f, r) = handle_op(inst, handle_mem_write, handle_reg_write, isInit)
            setinput += s
            feistel += f
            restore += r
            backup += b
            
            if DEBUG >= 2:
                print "******************************************************************************"
            print "count_R = %d, count_L = %d" % (count_r, count_l)
#             print "R = %d, L = %d" % (len(feistel_r), len(feistel_l))
            
            # Initialize feistel blocks for exception info
            if isInit:
                print "Ecpt blocks"
                l = get_addr(8)                
                feistel_l += l
                for val in l:
                    init_l += [gen_imm2mem(gen_seed(), "0x%x" % val)]
                print "******************************************************************************"
                while len(feistel_r) < len(feistel_l):
                    feistel_r += get_addr()
                    feistel_r_bak += get_addr()
            
            # Generate gadgets computing feistel ciphertext for exception data 
            src1 = "0x%x" % feistel_l[count_l]
            src2 = "0x%x" % edata
            dest = "0x%x" % feistel_r[count_l]
            feistel += [gen_feistel_cipher(src1, src2, dest, 4)]
            count_l += 1
            src1 = "0x%x" % feistel_l[count_l]
            src2 = "0x%x" % (edata + 4)
            dest = "0x%x" % feistel_r[count_l]
            feistel += [gen_feistel_cipher(src1, src2, dest, 4)]
            count_l += 1
                                                    
   
            if isInit:
                # NOTE: We handle the case where read > write there, while 
                # hanlding the opposite case in handle_$$$_write, since we need
                # enough read blocks to computer feistel ciphertext at that point   
                if DEBUG >= 2:
                    print "After parsing all operands, there are %d R blocks " \
                    "and %d L blocks" % (len(feistel_r), len(feistel_l))
                d = len(feistel_r) - len(feistel_l)
                if d > 0 and DEBUG >= 2:
                    print "Add %d more L blocks" % d
                while len(feistel_l) < len(feistel_r):
                    l = get_addr()
                    feistel_l += l
                    init_l += [gen_imm2mem(gen_seed(), "0x%x" % l[0])]
                assert(len(feistel_l) == len(feistel_r))
            
            # Copy value from additional L blocks to (next) R block
            while count_l < count_r:
                src = "0x%x" % feistel_l[count_l]
                dest = "0x%x" % feistel_r[count_l]
                feistel += [gen_store_mem(src, dest)]
                count_l += 1  
            
            #backup
            for idx, val in enumerate(feistel_r):                
                src = "0x%x" % val
                dest = "0x%x" % feistel_r_bak[idx]
                backup_r += [gen_store_mem(src, dest)]
            if isInit:
                #If 1st iter, mov init state input to R
                if MODE > 2:
                    assert(count_addr != 0)
                    init_r = init_r + [merge_glist(init_l, "Init L blocks")]
                set_r = init_r
                       
            # Update L blocks: moving R_{i-1} to L_{i} via R's backup
            for i in range(len(feistel_r_bak)):
                src = "0x%x" % feistel_r_bak[i]
                dest = "0x%x" % feistel_l[i]                
                update += [gen_store_mem(src, dest)]
            
            count_l = 0
            count_r = 0
            output = feistel;
        elif MODE >= 1:
        # simple aggregating mode
            (_, _, f, _) = handle_op(inst, copy_mem_write, copy_reg_write, isInit)
            output += f
            if DEBUG >= 2:
                print "Simple aggreg: handle outputs"            
                print "count_R = %d, count_L = %d" % (count_r, count_l)
                print "R = %d, L = %d" % (len(feistel_r), len(feistel_l))
        # else :Do nothing, for single test case mode

        l_restore = []
        return (backup, remove_none(set_r), remove_none(backup_r), setinput, \
                code, output, update, restore);     
    
        
    @staticmethod
    def gen_prologue(start, mid, snapshot, tcn, addr = None):
        asm = [];
        if MODE <= 2:
            asm = "invlpg 0x0;" \
                "prefetch 0x%s;" % tcn;
        else:
            # feistel looping mode
            assert (addr != None)
            asm = "movl $0x%.8x,%%%s:(0x%x); " \
                "forward_%.8x: " \
                "invlpg 0x0;" \
                "prefetch 0x%s;" % (LOOP, retseg, addr, start, tcn)
#         ds = in_snapshot_sreg("DS", snapshot)
#         asm += "mov $0x%.4x,%%ax; mov %%ax,%%ds;" % ds 
        # Copy the eip after tested insn to a global location
        asm += "movl $forward_%.8x,%%%s:(0x%x);" % (mid, retseg, retp)
        mnemonic = "prologue"
        return [Gadget(asm = asm, mnemonic = mnemonic)]


# ===-----------------------------------------------------------------------===
# Build a graph describing dependencies between gadgets
# ===-----------------------------------------------------------------------===
def build_dependency_graph(gadgets):
    dg = networkx.DiGraph()

    for g in gadgets:
        dg.add_node(g)

    for g0 in gadgets:
        if g0 != None:
            for g1 in gadgets:
                if g1 != g0 and g1 != None and g1.depend(g0):
                    dg.add_edge(g0, g1)

    return dg 
        
        
# ===-----------------------------------------------------------------------===
# Return the dependency graph in Graphviz format
# ===-----------------------------------------------------------------------===
def dot_dependency_graph(graph):
    r = "digraph G {"
    for n in graph:
        if n != None:
            r += "%u [label=\"%s\"];\n" % (id(n), n.mnemonic)

    for n in graph:
        if n != None:
            for s in graph[n]:
                r += "%u -> %u;\n" % (id(n), id(s))

    return r + "}\n"


# ===-----------------------------------------------------------------------===
# Return the nodes of the dependency graph in topological order (deterministic
# version)
#
# This function is a mere cut & paste of 
# networkx.algorithms.dag.topological_sort(). The only difference is in the
# order in which nodes are traversed. We sort them to ensure a deterministic
# topological ordering.
# ===-----------------------------------------------------------------------===
def topological_sort(graph):

    assert networkx.algorithms.dag.is_directed_acyclic_graph(graph)

    G = graph

    # nonrecursive version
    seen={}
    order_explored=[] # provide order and 
    explored={}       # fast search without more general priorityDictionary

    nodecmp = lambda x,y: cmp(x.mnemonic, y.mnemonic)

    nodes = [v for v in G]
    nodes.sort(nodecmp)
    for v in nodes:     # process all vertices in G
        if v in explored:
            continue
        fringe=[v]   # nodes yet to look at
        while fringe:
            w=fringe[-1]  # depth first search
            if w in explored: # already looked down this branch
                fringe.pop()
                continue
            seen[w]=1     # mark as seen
            # Check successors for cycles and for new nodes
            new_nodes=[]
            successors = G[w].keys()
            successors.sort(nodecmp)
            for n in successors:
                if n not in explored:
                    if n in seen: 
                        print n
                        print "find cycle"
                        return #CYCLE !!
                    new_nodes.append(n)
            if new_nodes:   # Add new_nodes to fringe
                fringe.extend(new_nodes)
            else:           # No new nodes so w is fully explored
                explored[w]=1
                order_explored.insert(0,w) # reverse order explored
                fringe.pop()    # done considering this node
    
    return order_explored


# ===-----------------------------------------------------------------------===
# Given a dependency graph, sort it in topological order
# ===-----------------------------------------------------------------------===
def sort_graph(depgraph, name):
        if DEBUG >= 3:
            name_ = "%s" % name
            path = "/tmp/depgraph_%s.dot" % name_.replace(" ","_")[:128]
            open(path, "w").write(dot_dependency_graph(depgraph))
    
        return topological_sort(depgraph)    

# ===-----------------------------------------------------------------------===
# A glue of sort_graph() and build_dependency_graph()
# ===-----------------------------------------------------------------------===
def sort_gadget(g):
    depgraph = build_dependency_graph(g)
    return sort_graph(depgraph, g)

# ===-----------------------------------------------------------------------===
# Given a gadget list ``g'', merge all the gadgets in g into one large gadget
# ===-----------------------------------------------------------------------===
def merge_glist(g, mnemonic = ""):
    if g == []:
        return None
    m = g[0]
    for e in g[1:]:
        m += e
    if mnemonic != "":
        m.mnemonic = mnemonic
        m.asm += "// %s" % mnemonic
    return m


# ===-----------------------------------------------------------------------===
# Compile a sequence of gadgets into x86 code
# ===-----------------------------------------------------------------------===
def compile_gadgets(gadget, epilogue, directive = ""):
    # Build a graph representing dependencies among gadgets and order the
    # gadgets to make sure all dependencies are satisfied
    asm = "";
    i = 0
    for tuple in gadget:
        (startup, pre, code, revert_, post, revert, loop) = tuple;

        # Generate the assembly code        
        for g in startup + pre + code + revert_ + post + revert + loop:
            if g != None:
                asm += "%s\n" % (g.asm)
                if i and i % 8 == 0:
                    r = random.randint(0, 0xffffffff)
                    asm += "jmp forward_%.8x; forward_%.8x:\n" % (r, r)
                i += 1

    #Add epilogue gadgets
    for g in epilogue:
        if g != None:
            asm += "%s\n" % (g.asm)
            if i and i % 8 == 0:
                r = random.randint(0, 0xffffffff)
                asm += "jmp forward_%.8x; forward_%.8x:\n" % (r, r)
            i += 1        
    # Assemble
    tmpobj = Tempfile()
    tmpelf = Tempfile()
    cmdline = "as -32 -o %s -" % tmpobj
    p = subprocess.Popen(cmdline.split(), 
                         stdin = subprocess.PIPE, 
                         stdout = subprocess.PIPE, 
                         stderr = subprocess.PIPE)
    prog = str("\n.text\n" + directive + "\n" + asm + "\n")    
    if DEBUG >= 3:
        print prog
    stdout, stderr = p.communicate(prog)
    if stderr != "":
        print "[E] Can't compile asm:\n%s\n-%s-" % (prog, stderr)
        exit(1)    
    #For correct direct jump location, use linker
    #.testcase start at 0x00219000 in base state kernel
    if DEBUG >= 3:
        cmdline = "readelf --relocs %s" % tmpobj
        subprocess.call(cmdline.split())
    cmdline = "ld -m elf_i386 -Ttext 0x219000 -e 0x219000 -o %s %s" % (tmpelf, tmpobj)
    subprocess.call(cmdline.split())

    # Extract the asm of the gadgets (.text section) from the elf object
    cmdline = "objcopy -O binary -j .text %s" % str(tmpelf)
    print "cmdlind: %s\n" % cmdline
    subprocess.call(cmdline.split())
    obj = open(str(tmpelf)).read()

    return asm, obj


# ===-----------------------------------------------------------------------===
# Patch the kernel executable
# ===-----------------------------------------------------------------------===
def patch_kernel(orig_kernel, where, obj, new_kernel):
    kernel = elf.Elf(orig_kernel)
    testcase = kernel.getSection(where)
    assert testcase is not None
    print "%d %d\n" % (len(obj), testcase.getSize())
    assert len(obj) < testcase.getSize()
    
    padding = "\xf4"*(testcase.getSize() - len(obj))

    obj  = kernel.getBytes(0, testcase.getOffset()) + obj + padding + \
        kernel.getBytes(testcase.getOffset() + testcase.getSize(), 
                        kernel.getSize())
    assert len(obj) == kernel.getSize()

    open(str(new_kernel), "w").write(obj)
    return new_kernel


# ===-----------------------------------------------------------------------===
# Generate a template of a bootable floppy image (with on-disk caching) 
# ===-----------------------------------------------------------------------===
def gen_floppy_template():
    l = lock(FLOPPY_TEMPLATE)
    
    if not isfile(FLOPPY_TEMPLATE) or \
            (mtime(FLOPPY_TEMPLATE) < max(mtime(KERNEL), mtime(__file__))):
        tmp = FLOPPY_TEMPLATE
        cmd = """\
dd if=/dev/zero of=%s bs=1024 count=1440 &&
/sbin/mkdosfs %s &&
mmd -i %s boot &&
mmd -i %s boot/grub &&
mcopy -i %s %s/boot/grub/* ::boot/grub""" % (tmp, tmp, tmp, tmp, tmp, GRUB)
        subprocess.check_call(cmd, shell = True, stdout = NULL, stderr = NULL)

        cfg = open("%s/grub.cfg" % GRUB).read().replace("floppy.img", str(tmp))
        cfg = Tempfile(suffix = ".cfg", data = cfg)

        cmd = """%s --no-pager --batch --device-map=/dev/null < %s""" % \
            (GRUB_EXE, cfg)
        subprocess.check_call(cmd, shell = True, stdout = NULL, stderr = NULL)

    l.release()
    
    return open(FLOPPY_TEMPLATE).read()


# ===-----------------------------------------------------------------------===
# Generate a bootable floppy image with a given kernel
# ===-----------------------------------------------------------------------===
def gen_floppy(kernel, floppy, cksum, testcase):
    cksum = Tempfile(data = cksum)
    testcase = Tempfile(data = testcase)

    open(str(floppy), "w").write(gen_floppy_template())

    cmd = """mcopy -o -i %s %s ::kernel && mcopy -o -i %s %s ::kernel.md5 && mcopy -o -i %s %s ::testcase.md5""" % \
        (floppy, kernel, floppy, cksum, floppy, testcase)
    print cmd
    subprocess.check_call(cmd, shell = True, stdout = NULL, stderr = NULL)

    return floppy


def to_str(l):
    return "".join(l)

def to_dword(w):
    w, = struct.unpack("I", to_str(w))
    return w

def to_word(w):
    w, = struct.unpack("H", to_str(w))
    return w

def from_dword(w):
    return list(struct.pack("I", w))

def from_word(w):
    return list(struct.pack("H", w))

def merge(o, v):
    assert len(o) == len(v)

    r = []
    for i in range(len(o)):
        if v[i] is None:
            r += [o[i]]
        else:
            r += [v[i]]

    return r

# ===-----------------------------------------------------------------------===
# Parse the testcase
# ===-----------------------------------------------------------------------===
def load_fuzzball_testcase(tc, snapshot):
    root = dirname(abspath(tc))
    shellcode = open(joinpath(root, "..", "shellcode")).read()
    snapshot_md5 = open(joinpath(root, "..", "snapshot")).read()
    exitstatus = open(joinpath(root, "exitstatus")).read().split("\n")
    exitstatus = [s.split("=") for s in exitstatus if s]

    tc = load_fuzzball_tc(tc, full = True)
    
    regs = []
    memlocs = []

    # If a piece of a register is missing use the original value from the
    # snapshot
    for (t, k), (v, s) in tc.iteritems():
        if isreg((t, k)):
            o = from_dword(in_snapshot_reg(k, snapshot))
            regs += [Register(k, to_dword(merge(o, v)))]
        elif issreg((t, k)):
            o = from_word(in_snapshot_sreg(k, snapshot))
            regs += [SegmentRegister(k, to_word(merge(o, v)))]
        elif isdreg((t, k)):
            o = from_dword(in_snapshot_dreg(k, snapshot))
            regs += [DebugRegister(k, to_dword(merge(o, v)))]
        elif iscreg((t, k)):
            o = from_dword(in_snapshot_creg(k, snapshot))
            regs += [ControlRegister(k, to_dword(merge(o, v)))]
        elif ismem((t, k)):
            memlocs += [Memory(int(k, 16), v[0], s)]

    return snapshot_md5, shellcode, exitstatus, regs, memlocs


# ===-----------------------------------------------------------------------===
# Transform a test-case generated by symbolic execution and into a bootable
# floppy image
# ===-----------------------------------------------------------------------===
def gen_floppy_with_testcase(testcase, kernel = None, floppy = None, mode = 0, loop = 1):
    global count_addr
    global MODE
    global LOOP
    global next_addr
    global start_addr
    global end_addr
    global PG
    
    LOOP = int(loop);
    MODE = int(mode);
    print "MODE = %d" % MODE
     
    if kernel:
        print "gen kernel"
    if floppy:
        print "gen floppy"
    assert isfile

    snapshot = cpustate_x86.X86Dump(open(SNAPSHOT).read())
    gadget = []
    
    count = 0
    num = len(testcase.split(","))
    for tc in testcase.split(","):     
        count += 1
        snapshot_md5, shellcode, exitstatus, regs, memlocs = \
            load_fuzzball_testcase(tc, snapshot)
    
        assert snapshot_md5 == md5(open(SNAPSHOT))
    
        eip = Register("EIP").in_snapshot(snapshot)
    
        print "="*columns()
        print "[*] %-36s %s" % ("Test-case", tc)
        print "[*] %-36s %s" % ("Snapshot", snapshot_md5)
        print "[*] %-36s '%s' '%s'" % ("Shellcode", disasm(shellcode, eip)[0], 
                                   hexstr(shellcode))
        for n, v in exitstatus:
            print "[*] %-36s %s" % (n[0].upper() + n[1:], v)
        print "[*] Registers"
        for reg in regs:
            name, value = reg.name, reg.value
            s = "    [*] %-32s %.8x" % (name, value)
            orig_value = reg.in_snapshot(snapshot) 
            if orig_value != value:
                print red(s + " [was %.8x]" % orig_value)
            else:
                print s
        print "[*] Memory"
        for mem in memlocs:
            addr, value, sym = mem.address, mem.value, mem.symbol
            size = len(value)
            s = "    [*] %-32s %r" % ("%.8x-%.8x [%s]" % 
                                         (addr, addr + size - 1, sym), value)
            orig_value = in_snapshot_mem((addr, size), snapshot) 
            if orig_value != value:
                print red(s + " [was %r]" % orig_value)
            else:
                print s
    
        if floppy or kernel:
            if kernel:
                print "[*] %-36s %s" % ("Kernel", kernel)
            if floppy:
                print "[*] %-36s %s" % ("Floppy", floppy)
                
        print "="*columns()
    
        param = []   # Set FuzzBALL-generated inputs (parameters)
        param0 = []     # set parameters for 0-th testcase
        revert = [] # Undo init state
        revert0 = [] # Undo init state for 0-th testcase
        revert_ = [] # A copy of revert; regenerate instead of copy because patch ljmp
        done = set()
        
        if count == 1:
            count_addr = get_addr()[0]
        
        # Labels of return points
        l0 = random.randint(0, 0xffffffff)  # label at the beginnign of this test case
        l1 = random.randint(0, 0xffffffff)  # lable of revert', a copy of revert
        l2 = random.randint(0, 0xffffffff)  # lable of post (feistel & restore)
        l3 = random.randint(0, 0xffffffff)  # lable of revert
        l4 = random.randint(0, 0xffffffff)  # label of loop
        l5 = random.randint(0, 0xffffffff)  # label at the end of this test case
        ls = random.randint(0, 0xffffffff)  # start of loop 

        startup = Gadget.gen_prologue(l0, l3, snapshot, tc.split("/")[-2], count_addr)

        (backup, set_r, copy_r, setinput, code, output, update, restore) \
                = Gadget.gen_root(snapshot, shellcode, count)

        # Generate code for initializing registers and memory locations
        for rm in regs + memlocs:
            orig_value = rm.in_snapshot(snapshot)
            if orig_value != rm.value:
                param += rm.gen_gadget(snapshot)
                param0 += rm.gen_gadget(snapshot)
                revert += rm.gen_revert_gadget(snapshot)
                revert0 += rm.gen_revert_gadget(snapshot)
                revert_ += rm.gen_revert_gadget(snapshot)
                done.add(rm)

        param = make_stable(param, done, snapshot)
        param0 = make_stable(param0, done, snapshot)
        revert = make_stable(revert, done, snapshot)
        revert0 = make_stable(revert0, done, snapshot)
        revert_ = make_stable(revert_, done, snapshot)

        asm = "jmp forward_%.8x;" % l2 # jump over revert' and execute post
        code += [Gadget(asm = asm, mnemonic = "jump to post")]

        if copy_r != []:
            asm = "push %eax;"
            copy_r = [Gadget(asm = asm, mnemonic = "")] + copy_r
            asm = "pop %eax;"
            copy_r += [Gadget(asm = asm, mnemonic = "")]
            for g in copy_r:
                g.kill -= set([Register("EAX")])

        if MODE <= 0:
            param0 = []
            revert_ = []
            revert0 = []
            revert = []

        # Copy initial inputs of 1st testcase to R block
        if count == 1:
            set_r = param0 + set_r
            set_r = sort_gadget(set_r)
            startup += set_r
            startup += sort_gadget(revert0)
        
        #jump to TC beginning for a fixed # of times                   
        asm = "";
        if MODE > 2:
            asm = "decl %%%s:0x%x; " \
                "jnz forward_%.8x; // back to loop entrance" % (retseg, count_addr, ls)
        loop = [Gadget(asm = asm, mnemonic = "loop")] 
                       
        # Sort gadgets & add labels to return points
        if setinput != []:            
            asm = "movl $forward_%.8x,%%%s:(0x%x);" % (l2, retseg, retp)
            setinput = [Gadget(asm = asm, mnemonic = "return to post")] + setinput
            setinput = sort_gadget(setinput)

        #pre = [merge_glist(backup, "backup"), merge_glist(copy_r, "copy R blocks"), \
        pre = backup + [merge_glist(copy_r, "copy R blocks to R'")] + setinput
        pre = remove_none(param + pre)        
        pre = sort_gadget(pre)
        pre = [Gadget(asm = "forward_%.8x:" % ls, mnemonic = "loop start point")] + pre

        post = output + restore
        post = sort_gadget(post)
        post += update
        revert = sort_gadget(revert)    
        revert_ = sort_gadget(revert_)

        asm = "movl $forward_%.8x,%%%s:(0x%x);" % (l1, retseg, retp)
        code = [Gadget(asm = asm, mnemonic = "return to revert_")] + code
        asm = "movl $forward_%.8x,%%%s:(0x%x);" % (l2, retseg, retp)
        revert_ = [Gadget(asm = asm, mnemonic = "return to post")] + revert_
        asm = "movl $forward_%.8x,%%%s:(0x%x);" % (l3, retseg, retp)
        post = [Gadget(asm = asm, mnemonic = "return to revert")] + post
        asm = "movl $forward_%.8x,%%%s:(0x%x);" % (l4, retseg, retp)
        revert = [Gadget(asm = asm, mnemonic = "return to loop")] + revert
        asm = "movl $forward_%.8x,%%%s:(0x%x);" % (l5, retseg, retp)
        loop = [Gadget(asm = asm, mnemonic = "return to end")] + loop
        
        asm = "forward_%.8x:" % l1
        revert_ = [Gadget(asm = asm, mnemonic = "revert_")] + revert_
        asm = "forward_%.8x:" % l2
        post = [Gadget(asm = asm, mnemonic = "restore")] + post
        asm = "forward_%.8x:" % l3
        revert = [Gadget(asm = asm, mnemonic = "revert")] + revert
        asm = "forward_%.8x:" % l4
        loop = [Gadget(asm = asm, mnemonic = "loop")] + loop
        asm = "forward_%.8x:" % l5
        loop += [Gadget(asm = asm, mnemonic = "End of testcase")]

        gadget.append((startup, pre, code, revert_, post, revert, loop))

        if PG == 0:
            PG = 1
            print "Turn paging back on"
            flip_addrs()

    epilogue = Gadget.gen_end_testcase()
    print_feistel_blocks()

    
    code, obj = compile_gadgets(gadget, epilogue)

    if DEBUG >= 2:
        print "="*columns()
        print 
        print code

    if not (kernel or floppy):
        return
        
    if not kernel:
        kernel = Tempfile()

    kernel = patch_kernel(KERNEL, TESTCASE, obj, kernel)

    if floppy:
        floppy = gen_floppy(kernel, floppy, md5(open(KERNEL)), md5(obj))


if __name__ == "__main__":
    t0 = time.time()

    opts = {"testcase" : None, "kernel" : None, "floppy" : None, "mode" : 0, "loop" : 1}
    extraopts = {"debug" : 0}

    for arg in sys.argv[1:]:
        a = arg.split(":")
        assert len(a) == 2
        k, v = a
        if k in opts:
            opts[k] = v
        elif k in extraopts:
            extraopts[k] = v
        else:
            assert 0

    DEBUG = int(extraopts["debug"])

    gen_floppy_with_testcase(**opts)

    print >> sys.stderr, "Done in %.3fs" % (time.time() - t0)
