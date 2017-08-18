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
retp = 0x1278008      # The location to store current return point for ecpt handler
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
loop = 1            #repeat testing each test case for a number of times


# ===-----------------------------------------------------------------------===
# Other global variables
# ===-----------------------------------------------------------------------===
l_insn = None       # Label at the tested instruction
l_restore = []      # list of inputs/outputs for which a pair of backup/restore
                    # gadgets has been generated  


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


reg_map = [
  "",
  "bndcfgu",
  "bndstatus",
  "bnd0",
  "bnd1",
  "bnd2",
  "bnd3",
  "cr0",
  "cr1",
  "cr2",
  "cr3",
  "cr4",
  "cr5",
  "cr6",
  "cr7",
  "cr8",
  "cr9",
  "cr10",
  "cr11",
  "cr12",
  "cr13",
  "cr14",
  "cr15",
  "dr0",
  "dr1",
  "dr2",
  "dr3",
  "dr4",
  "dr5",
  "dr6",
  "dr7",
  "dr8",
  "dr9",
  "dr10",
  "dr11",
  "dr12",
  "dr13",
  "dr14",
  "dr15",
  "flags",
  "eflags",
  "rflags",
  "ax",
  "cx",
  "dx",
  "bx",
  "sp",
  "bp",
  "si",
  "di",
  "r8w",
  "r9w",
  "r10w",
  "r11w",
  "r12w",
  "r13w",
  "r14w",
  "r15w",
  "eax",
  "ecx",
  "edx",
  "ebx",
  "esp",
  "ebp",
  "esi",
  "edi",
  "r8d",
  "r9d",
  "r10d",
  "r11d",
  "r12d",
  "r13d",
  "r14d",
  "r15d",
  "rax",
  "rcx",
  "rdx",
  "rbx",
  "rsp",
  "rbp",
  "rsi",
  "rdi",
  "r8",
  "r9",
  "r10",
  "r11",
  "r12",
  "r13",
  "r14",
  "r15",
  "al",
  "cl",
  "dl",
  "bl",
  "spl",
  "bpl",
  "sil",
  "dil",
  "r8b",
  "r9b",
  "r10b",
  "r11b",
  "r12b",
  "r13b",
  "r14b",
  "r15b",
  "ah",
  "ch",
  "dh",
  "bh",
  "error",
  "rip",
  "eip",
  "ip",
  "k0",
  "k1",
  "k2",
  "k3",
  "k4",
  "k5",
  "k6",
  "k7",
  "mm0",
  "mm1",
  "mm2",
  "mm3",
  "mm4",
  "mm5",
  "mm6",
  "mm7",
  "mxcsr",
  "", #"stackpush",
  "", #"stackpop",
  "gdtr",
  "ldtr",
  "idtr",
  "tr",
  "tsc",
  "tscaux",
  "msrs",
  "fsbase",
  "gsbase",
  "x87control",
  "x87status",
  "x87tag",
  "x87push",
  "x87pop",
  "x87pop2",
  "x87opcode",
  "x87lastcs",
  "x87lastip",
  "x87lastds",
  "x87lastdp",
  "cs",
  "ds",
  "es",
  "ss",
  "fs",
  "gs",
  "tmp0",
  "tmp1",
  "tmp2",
  "tmp3",
  "tmp4",
  "tmp5",
  "tmp6",
  "tmp7",
  "tmp8",
  "tmp9",
  "tmp10",
  "tmp11",
  "tmp12",
  "tmp13",
  "tmp14",
  "tmp15",
  "st(0)",
  "st(1)",
  "st(2)",
  "st(3)",
  "st(4)",
  "st(5)",
  "st(6)",
  "st(7)",
  "xcr0",
  "xmm0",
  "xmm1",
  "xmm2",
  "xmm3",
  "xmm4",
  "xmm5",
  "xmm6",
  "xmm7",
  "xmm8",
  "xmm9",
  "xmm10",
  "xmm11",
  "xmm12",
  "xmm13",
  "xmm14",
  "xmm15",
  "xmm16",
  "xmm17",
  "xmm18",
  "xmm19",
  "xmm20",
  "xmm21",
  "xmm22",
  "xmm23",
  "xmm24",
  "xmm25",
  "xmm26",
  "xmm27",
  "xmm28",
  "xmm29",
  "xmm30",
  "xmm31",
  "ymm0",
  "ymm1",
  "ymm2",
  "ymm3",
  "ymm4",
  "ymm5",
  "ymm6",
  "ymm7",
  "ymm8",
  "ymm9",
  "ymm10",
  "ymm11",
  "ymm12",
  "ymm13",
  "ymm14",
  "ymm15",
  "ymm16",
  "ymm17",
  "ymm18",
  "ymm19",
  "ymm20",
  "ymm21",
  "ymm22",
  "ymm23",
  "ymm24",
  "ymm25",
  "ymm26",
  "ymm27",
  "ymm28",
  "ymm29",
  "ymm30",
  "ymm31",
  "zmm0",
  "zmm1",
  "zmm2",
  "zmm3",
  "zmm4",
  "zmm5",
  "zmm6",
  "zmm7",
  "zmm8",
  "zmm9",
  "zmm10",
  "zmm11",
  "zmm12",
  "zmm13",
  "zmm14",
  "zmm15",
  "zmm16",
  "zmm17",
  "zmm18",
  "zmm19",
  "zmm20",
  "zmm21",
  "zmm22",
  "zmm23",
  "zmm24",
  "zmm25",
  "zmm26",
  "zmm27",
  "zmm28",
  "zmm29",
  "zmm30",
  "zmm31",
  "",
  "bndcfgu", 
  "bndcfgu", 
  "bndstatus", 
  "bndstatus", 
  "bnd0", 
  "bnd3", 
  "cr0", 
  "cr15", 
  "dr0", 
  "dr15", 
  "flags", 
  "rflags", 
  "ax", 
  "r15w", 
  "eax", 
  "r15d", 
  "rax", 
  "r15", 
  "al", 
  "r15b", 
  "ah", 
  "bh", 
  "invalid", 
  "error", 
  "rip", 
  "ip", 
  "k0", 
  "k7", 
  "mmx0", 
  "mmx7", 
  "mxcsr", 
  "mxcsr", 
  "", #"stackpush", 
  "gsbase", 
  "x87control", 
  "x87lastdp", 
  "cs", 
  "gs", 
  "tmp0", 
  "tmp15", 
  "st0", 
  "st7", 
  "xcr0", 
  "xcr0", 
  "xmm0", 
  "xmm31", 
  "ymm0", 
  "ymm31", 
  "zmm0", 
  "zmm31" 
]

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

# ===-------------------------------------------------------------------===
# Return the next register of the same typethat are not used. 
# `l` is the list of used registers
# NOTE: Only support frequently used registers; Add more registers on demand
# ===-------------------------------------------------------------------===
def get_unused_reg(l):
    s = []
    if reg_map.index(l[0]) in range(reg_map.index("mm0"), reg_map.index("mm7")):
        s = list(range(reg_map.index("mm0"), reg_map.index("mm7")))
    elif reg_map.index(l[0]) in range(reg_map.index("xmm0"), reg_map.index("xmm31")):
        s = list(range(reg_map.index("xmm0"), reg_map.index("xmm31")))
    elif reg_map.index(l[0]) in range(reg_map.index("eax"), reg_map.index("ebx")):
        s = list(range(reg_map.index("eax"), reg_map.index("ebx")))
    else:
        return None
    for e in l:
        if reg_map.index(e) in s:
            s.remove(reg_map.index(e))
    return s[0]


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
def resize_reg(r, size):
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
    except Exception as (e, s):
        assert 0, "Illegal register size - %s size %d" % (e, s)
    return reg
                    
        

# ===-------------------------------------------------------------------===
# Generate code in text format that mov 32 bits from mem addr1 to mem addr2 
# via eax, and then *clean addr1
# ===-------------------------------------------------------------------===
def gen_store_mem_asm(src, dest):
    r = "ecx" if any(x in src for x in ["eax", "ax", "ah", "al"]) or \
            any(x in dest for x in ["eax", "ax", "ah", "al"]) else "eax"
    asm = "mov %s,%%%s;" \
        "mov %%%s,%s;" % (src, r, r, dest)
    return asm


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
def gen_cmp_imm_asm(src, imm, t = "eax", size = 4):
    asm = ""
    if src in reg_map:
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
            asm += gen_reg2mem_asm(reg, "0x%x" % l[0], size)
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
    return asm

# ===-------------------------------------------------------------------===
# Generate code in text format to compare a reg with a mem location
# ===-------------------------------------------------------------------===
def gen_cmp_reg2mem_asm(reg, mem, t = "eax", size = 4):
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
    return asm



# ===-------------------------------------------------------------------===
# Generate code in text format to copy from src reg to mem dest
# ===-------------------------------------------------------------------===
def gen_reg2mem_asm(reg, mem, size = 4):
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
        if reg == "st(0)":
            asm += "fstp %s;" % mem
        else:
            asm += "fxch %%%s;" \
                "fstp %s;" \
                "fxch %%%s;" % (reg, mem, reg)
    elif reg == "xcr0":
        asm += "xgetbv;" \
            "mov %%edx,%s;" \
            "mov %%eax,%s+0x4;" % (mem, mem)
    else:
        op = size2mov(size, reg)
        r = resize_reg(reg, size)
        asm += "%s %%%s,%s;" % (op, r, mem)
    return asm


# ===-------------------------------------------------------------------===
# Generate code in text format to copy from mem src to dest reg
# ===-------------------------------------------------------------------===
def gen_mem2reg_asm(mem, reg, size = 4):
    asm = ""
    if reg == "eflags":
        asm += "andl $0xad5,%s;" \
            "push %s;" \
            "popf;" % (mem, mem)
    elif reg in ["eip", "ip", "cs", "tr"]:
        return ""
    elif reg == "mxcsr":
        asm += "ldmxcsr %s;" % mem
    elif reg.startswith("cr") or reg.startswith("dr"):
        asm += "mov %s,%%eax;" \
            "mov %%eax,%%%s;" % (mem, reg)
    elif reg.startswith("st"):
        if reg == "st(0)":
            asm += "fld %s;" % mem
        else:
            asm += "fxch %%%s;" \
                "fld %s;" \
                "fxch %%%s;" % (reg, mem, reg)
    elif reg == "xcr0":
        asm += "mov %s,%%edx;" \
            "mov %s+0x4,%%eax;" \
            "xsetbv;" % (mem, mem)
    else:
        op = size2mov(size, reg)
        r = resize_reg(reg, size)
        asm += "%s %s,%%%s;" % (op, mem, r)         
    return asm


# ===-------------------------------------------------------------------===
# Generate code in text format to store current flags to memory
# ===-------------------------------------------------------------------===
def gen_store_eflags_asm(dest):
    asm = "pushf; " \
        "pop %s;" % dest
    return asm


# ===-------------------------------------------------------------------===
# Generate code in text format to store immediate value to 32-bit memory
# ===-------------------------------------------------------------------===
def gen_imm2mem_asm(imm, dest):
    asm = "movl $0x%.8x,%s;" % (imm, dest)
    return asm


# ===-------------------------------------------------------------------===
# Generate gadget that mov from mem addr1 to mme addr2 via eax
# then *clean addr1
# ===-------------------------------------------------------------------===
def gen_store_mem(src, dest):
    asm = gen_store_mem_asm(src, dest)
    kill = []
    define = [dest]
    use = [src]
    r = "ecx" if any(x in src for x in ["eax", "ax", "ah", "al"]) or \
            any(x in dest for x in ["eax", "ax", "ah", "al"]) else "eax"
    if any(x in src for x in ["eax", "ax", "al", "ah"]):
        use += [Register("EAX")]
    kill += [Register(r.upper())]
    g = Gadget(asm = asm, mnemonic = "copy mem", define = define, \
            kill = kill, use = use)
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
    asm = gen_cmp_reg2mem_asm(reg, mem, t, size)
    if reg == "xcr0":
        kill += [Register("EAX"), Register("EDX")]
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
# Generate gadget to store current flags to memory
# ===-------------------------------------------------------------------===
def gen_store_eflags(dest):
    asm = gen_store_eflags_asm(dest)
    g = Gadget(asm = asm, mnemonic = "store flags")      
    return g 


# ===-------------------------------------------------------------------===
# Generate gadget to store immediate value to 32-bit memory
# ===-------------------------------------------------------------------===
def gen_imm2mem(imm, dest):
    asm = gen_imm2mem_asm(imm, dest)
    define = [dest]
    use = []
    kill = []    
    g = Gadget(asm = asm, mnemonic = "copy imm", define = define, \
            kill = kill, use = use)
    return g 


# ===-------------------------------------------------------------------===
# Generate gadget to copy from src reg to mem dest
# ===-------------------------------------------------------------------===
def gen_reg2mem(src, dest, size = 4):
    asm = gen_reg2mem_asm(src, dest, size)
    print asm
    if asm == "":
        return None
    else:
        kill = []
        use = [Register(src.upper())]
        define = [dest]        
        if any(x in dest for x in ["eax", "ax", "al", "ah"]):
            use += [Register("EAX")]
        if src.startswith("st"):
            use += [Register("CR0")]
        if src == "eflags":
            use += [Register("EFLAGS")]
        g = Gadget(asm = asm, mnemonic = "reg2mem", define = define, kill = [], use = use) 
        return g 


# ===-------------------------------------------------------------------===
# Generate gadget to copy from mem src to dest reg
# ===-------------------------------------------------------------------===
def gen_mem2reg(src, dest, size = 4):
    asm = gen_mem2reg_asm(src, dest, size)
    if asm == "":
        return None
    else:
        use = [src]
        define = [Register(dest.upper())]
        kill = []
        if any(x in src for x in ["eax", "ax", "al", "ah"]):
            use += [Register("EAX")]
        if dest.startswith("st"):
            use += [Register("CR0")]
            define += [Register("ST(0)")]
        g = Gadget(asm = asm, mnemonic = "mem2reg", define = define,\
                kill = kill, use = use)
        return g 


# ===-------------------------------------------------------------------===
# Generate gadget that xor src1 to src2, and copy the result(in src2) to dest
# Usually src1 and dest are mem locations while src2 can be either mem or reg 
# NOTE: Xed info is not enough for this funcion, since it cannot tell registers
# that cannot be XORed directly.
# TODO: No idea why need `clean`. Figure it out and remove it if not necessary
# ===-------------------------------------------------------------------===
def gen_feistel_cipher(src1, src2, dest, size = 4, clean = False):
    global l_insn
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
    if src2 in reg_map:
        use += [Register(src2.upper())]
    else:
        use += [src2]
    if any(x in src2 for x in ["eax", "ax", "al", "ah"]):
        use += [Register("EAX")]
    
    if src2 == "eflags":
        r = "0x%x" % get_addr(4, True)[0]
        asm2 += gen_store_eflags_asm(r)
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
        asm2 += gen_reg2mem_asm(src2, d, 8)        
        kill += [Register("EAX"), Register("EDX")]
        asm2 += "pxor %s,%%%s;" % (d, t)

    else:
        m = size2mov(size, src2)
        x = size2xor(size, src2)
        r = resize_reg(t, size)
        format_str = "%s %%%s,%%%s;" if src2 in reg_map else "%s %s,%%%s;" 
        asm2 += format_str % (x, src2, r)
        if clean:
            if src2 in reg_map:
                g3.asm += "%s %%%s,%%%s;" % (x, src2, src2)
            else:
                l = random.randint(0, 0xffffffff)            
                g3.asm += gen_cmp_imm_asm(src2, 0, t)
                g3.asm += "je forward_%.8x;" % l
                g3.asm += "%s %%%s,%%%s;"\
                        "%s %%%s,%s;" % (x, r, r, m, r, src2)
                g3.asm += "forward_%.8x:" % l
    g2 = Gadget(asm = asm2, mnemonic = "feistel", define = define, kill= kill, use = use)
    g = merge_glist([g1, g2, g3])
    g.kill = g.kill | set([Register(t.upper())])
    g.define -= set([Register(t.upper())])
    if src2 in ["eax", "ax", "al", "ah", "eflags"]:
        g.asm = "push %eax; push %ecx;" + g.asm + "pop %ecx; pop %eax;"
        g.kill = g.kill - set([Register("EAX"), Register("ECX")])
    return g


# ===-------------------------------------------------------------------===
# Get the operand string specified by `op` and `i` of instruction `inst`
# Operand can be either memmory or register
# The 2nd return value := whether this operand is memory accessing
# ===-------------------------------------------------------------------===
def get_op(inst, i):
    op = inst.get_operand(i)
    isMem = True
    # TODO: check i range before get_operand
    (op_str, _) = get_mem_op(inst, op, i)
    if op_str == "":
        (op_str, _) = get_reg_op(inst, op, i)
        isMem = False
    return (op_str, isMem)


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
                print "Find explicit!!!"
                if op.is_register() or op.is_memory_addressing_register():                 
                    print "    reg"
                    (op_str, op_len) = get_reg_op(inst, op, i)
                    if op_str == "" or op_len == 0:
                        return (None, 0, False)
                    else:
                        return (op_str, op_len, False)
                elif name in ["XED_OPERAND_AGEN", "XED_OPERAND_MEM0", "XED_OPERAND_MEM1"]:
                    print "    mem"
                    (op_str, op_len) = get_mem_op(inst, op, i)
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
    if disp_len != 0 or \
    not (reg_map[seg] != "" and reg_map[seg] != "ds"):  #displacement bits
        op_str += "0x%x" % (offset + d)
    if base != 0:
        op_str += "(%%%s" % reg_map[base]
        if reg_map[indx] != "" and iclass != "XED_ICLASS_XLAT":
            op_str += ",%%%s" % reg_map[indx]
        if scale != 0 and iclass != "XED_ICLASS_XLAT":
            op_str += ",%d" % scale
        op_str += ")"    
#     op_len = inst.get_operand_length_bits(i)
    op_len = inst.get_operand_length(i)
    return (op_str, op_len)    


def handle_mem_read(inst, op, i, isInit = False):
    global l_restore
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
    (op_str, op_len) = get_mem_op(inst, op, i)
    if DEBUG >= 2:
        print "handle_mem_read    %s, %d" % (op_str, op_len)    
    if inst.is_mem_read(0):
        f = get_addr(op_len)
        r_bak = get_addr(op_len)
        bak = get_addr(op_len)
        assert(len(f) == len(r_bak))
        for idx, val in enumerate(f):
            (op_str, _) = get_mem_op(inst, op, i, (idx * 4))
            if isInit:             
                feistel_r += [val]
                feistel_r_bak += [r_bak[idx]]
                feistel_in += [bak[idx]]
                r = "0x%x" % feistel_r[count_r]                
                init_r += [gen_store_mem(op_str, r)]
            src = "0x%x" % feistel_r[count_r]
            op_bak = "0x%x" % feistel_in[count_r]
            setinput += [gen_store_mem(src, op_str)]

            if not op_str in l_restore:
                l_restore += [op_str]
                backup += [gen_store_mem(op_str, op_bak)]
                restore_ = []
                l = random.randint(0, 0xffffffff)
                restore_ += [gen_cmp_mem(op_str, op_bak)]
                asm = "je forward_%.8x;" % l
                restore_ += [Gadget(asm = asm, mnemonic = "")]
                restore_ += [gen_store_mem(op_bak, op_str)]
                asm = "forward_%.8x:" % l
                restore_ += [Gadget(asm = asm, mnemonic = "")]
                restore += [merge_glist(restore_, "restore inputs")]

            count_r += 1  
    return (backup, setinput, feistel, restore)
    
    
def handle_mem_write(inst, op, i, isInit = False):
    global l_restore
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
    
    (op_str, op_len) = get_mem_op(inst, op, i)
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
            (src2, _) = get_mem_op(inst, op, i, j * 4)
            op_bak = "0x%x" % feistel_out[count_l + j]
            dest = "0x%x" % feistel_r[count_l + j]        
            feistel += [gen_feistel_cipher(src1, src2, dest, 4)]

            if not op_str in l_restore: 
                l_restore += [op_str]
                backup += [gen_store_mem(src2, op_bak)]
                restore_ = []
                l = random.randint(0, 0xffffffff)
                restore_ += [gen_cmp_mem(src2, op_bak)]
                asm = "je forward_%.8x;" % l
                restore_ += [Gadget(asm = asm, mnemonic = "")]
                restore_ += [gen_store_mem(op_bak, src2)]
                asm = "forward_%.8x:" % l
                restore_ += [Gadget(asm = asm, mnemonic = "")]
                restore += [merge_glist(restore_, "restore outputs")]
        count_l += r
        
    return (backup, setinput, feistel, restore)


# ===-------------------------------------------------------------------===
# Handle an register operand for feistel aggregated PokeEMU
# ===-------------------------------------------------------------------===
def get_reg_op(inst, op, i):  
    reg = inst.get_reg(op.get_name())
    reg_str = reg_map[reg]
#     reg_len = inst.get_operand_length_bits(i)
    reg_len = inst.get_operand_length(i)
#     print "REGISTER %s (%d)" %(reg_str, reg_len)
    return (reg_str, reg_len)


def handle_reg_read(inst, op, i, isInit = False):
    global l_restore
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
            print "r = %s" % r
            init_r += [gen_reg2mem(reg_str, r, reg_len)] 
            print init_r       
        size = int(math.ceil(float(reg_len) / 4))                        
        src = "0x%x" % feistel_r[count_r]
        print "src = %s" % src
        reg_bak = "0x%x" % feistel_in[count_r]
        setinput += [gen_mem2reg(src, reg_str, reg_len)]

        if not reg_str in l_restore:
            l_restore += [reg_str]
            backup += [gen_reg2mem(reg_str, reg_bak, reg_len)]
            restore_ = []
            t = "ecx" if reg_str in ["eax", "ax", "ah", "al"] else "eax"
            restore_ += [gen_mem2reg(reg_bak, reg_str, reg_len)]
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
    
    # Eip will be stored in eax
#     print "handle_reg_write: reg_str = %s" % reg_str
#     if reg_str in ["eip", "ip"]:
#         reg_str = "eax"
        
        
#     opcode = get_category(inst.get_category())
#     if opcode == "XED_CATEGORY_CALL":
        
    if op.is_written_only() or op.is_read_and_written():
        if op.is_written_only():
            print "W"
        elif op.is_read_and_written():
            print "RW"
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
            backup += [gen_reg2mem(reg_str, reg_bak, reg_len)]
            restore_ = []
            t = "ecx" if reg_str in ["eax", "ax", "ah", "al"] else "eax" 
            restore_ += [gen_mem2reg(reg_bak, reg_str, reg_len)]
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
    (op_str, op_len) = get_mem_op(inst, op, i)
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
        return hash(self.name)

    def __eq__(lhs, rhs):
        return lhs.name == rhs.name

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
        return self.gen_gadget(snapshot)    


# ===-----------------------------------------------------------------------===
# Snippets of code for setting the state of the CPU
# ===-----------------------------------------------------------------------===
class Gadget:
    def __init__(self, asm, mnemonic, define = None, kill = None, use = None, affect = None):
        self.asm = asm
        self.mnemonic = mnemonic

        if define is None: define = set()
        self.define = set(define)
        if kill is None: kill = set()
        self.kill = set(kill)
        if use is None: use = set()
        self.use = set(use)
        if affect is None: affect = set()
        self.affect = set(affect)

    def __str__(self):
        r = "Gadget '%s'\n" % (self.mnemonic)
        r += "   [*] asm:    %s\n" % (self.asm)
        r += "   [*] define: %s\n" % (", ".join([str(d) for d in self.define]))
        r += "   [*] kill:   %s\n" % (", ".join([str(k) for k in self.kill]))
        r += "   [*] use:    %s\n" % (", ".join([str(u) for u in self.use]))
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
        affect = self.affect | other.affect

        # Remove cycles
        define -= other.kill
        use -= other.kill
        use -= self.kill
        use -= (self.define & other.use)
        kill -= (self.kill & other.define)
        
        g = Gadget(asm, mnemonic, define, kill, use, affect)
        return g

    def __repr__(self):
        return self.mnemonic

    # ===-------------------------------------------------------------------===
    # Return true (= g1 define g0 / add edge (g0, g1)) if any of the followings is true:
    # * g1 defines what g0 kills 
    # * g0 uses what g1 defines
    # * (New)g0 use what g1 affects
    # ===-------------------------------------------------------------------===
    def depend(g1, g0):
        return (g1.define & g0.kill) or \
            (g0.use & g1.define or "*" in g1.define) or \
            (g1.affect & g0.use) or (g0.use & g1.kill) or \
            (Register("EFLAGS") in g0.use and not Register("EFLAGS") in g1.use) 
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
    def gen_set_mem(mem, snapshot):
        gadgets = []
        data = mem.value
        addr = mem.address
        sym = mem.symbol
        invlpg = ""
        for i in range(len(data)):
            define = [mem]
            #use = ["mem*"]
            use = []
            kill = []
            affect = []

            if sym: sym_ = sym
            else: sym_ = hex(addr)

            if sym.startswith("PDE_") or sym.startswith("PTE_"):
                entry = int(sym.split("_")[1])
                page = entry << 22
                invlpg = " mov %cr3,%eax; mov %eax,%cr3;"
                kill += [Register("EAX")]
                if sym.startswith("PDE_"):
                    use += ["pde"]
                    affect += ["pte", "gdt", "mem*"]
                else:
                    use += ["pte"]
                    affect += ["gdt", "mem*"]
            # elif sym.startswith("PTE_"):
            #     deref4 = lambda x: deref(x, 0, 4)
            #     cr3 = in_snapshot_creg("CR3", snapshot) & 0xfffff000
            #     pde0 = in_snapshot_mem((cr3, 4), snapshot)
            #     pte0 = struct.unpack("I", pde0)[0] & 0xfffff000
            #     print hex(pte0)
            #     j = ((addr - pte0) / 4) << 12
            #     invlpg = " invlpg 0x%x;" % j
            

            asm = "movb $0x%.2x,0x%.8x;%s // %s + %d" % \
                    (ord(data[i]), addr + i, invlpg, sym_, i);
            mnemonic = "%.8x %s" % (addr + i, sym)

            # If address belongs to the GDT kill the corresponding segment
            # selector
            if isgdt(sym):
                use += ["gdt"]
                affect += ["mem*"]
                idx = int(sym.split("_")[1])
                sregs = [SegmentRegister(r) for r in \
                             ["DS", "CS", "SS", "ES", "FS", "GS"]]
                for sreg in sregs:
                    sel = sreg.in_snapshot(snapshot) >> 3
                    if sel == idx:
                        kill += [sreg]
            if use == []:
                use += ["mem*"]
            gadgets += [Gadget(asm = asm, mnemonic = mnemonic, define = define,
                               kill = kill, use = use, affect = affect)]

        return gadgets

    
    # ===-------------------------------------------------------------------===
    # Generate a gadget to notify the end of the testcase
    # ===-------------------------------------------------------------------===
    @staticmethod
    def gen_end_testcase():
        r = random.randint(0, 0xffffffff)
        asm = "jmp forward_%.8x;forward_%.8x:" \
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
        output = []    # Handle output of the core insn. In feistel mode it compute XOR and copy it to L block* 
        restore = []
        
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
                    init_r = init_r + init_l
                set_r = init_r
                       
            #feistel restore: moving R_{i-1} to L_{i} via R's backup
            frestore = []
            for i in range(len(feistel_r_bak)):
                src = "0x%x" % feistel_r_bak[i]
                dest = "0x%x" % feistel_l[i]                
                frestore += [gen_store_mem(src, dest)]
            
            count_l = 0
            count_r = 0
            output = feistel + frestore;
        elif MODE >= 1:
        # simple aggregating mode
            (_, _, f, _) = handle_op(inst, copy_mem_write, copy_reg_write, isInit)
            output += f
            if DEBUG >= 2:
                print "Simple aggreg: handle outputs"            
                print "count_R = %d, count_L = %d" % (count_r, count_l)
                print "R = %d, L = %d" % (len(feistel_r), len(feistel_l))
        # else :Do nothing, for single test case mode
	
        return (backup, remove_none(set_r), remove_none(backup_r), setinput, \
                code, output, restore);     
    
        
    @staticmethod
    def gen_prologue(start, mid, snapshot, tcn, addr = None):
        asm = [];
        if MODE <= 2:
            asm = "invlpg 0x0;" \
                "prefetch 0x%s;" % tcn;
        else:
            # feistel looping mode
            assert (addr != None)
            asm = "movl $0x%.8x,0x%x; " \
                "forward_%.8x: " \
                "invlpg 0x0;" \
                "prefetch 0x%s;" % (loop, addr, start, tcn) 
#         ds = in_snapshot_sreg("DS", snapshot)
#         asm += "mov $0x%.4x,%%ax; mov %%ax,%%ds;" % ds 
        # Copy the eip after tested insn to a global location
        asm += "movl $forward_%.8x,0x%x;" % (mid, retp)
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
def sort_gadget(depgraph, name):
        if DEBUG >= 3:
            name_ = "%s" % name
            path = "/tmp/depgraph_%s.dot" % name_.replace(" ","_")[:128]
            open(path, "w").write(dot_dependency_graph(depgraph))
    
        return topological_sort(depgraph)    

# ===-----------------------------------------------------------------------===
# Given a list of Gadgets, sort it in topological order and 
# remove irrelavant Gadgets 
# ===-----------------------------------------------------------------------===
def get_subtree(g, name):
    sort = []
    depgraph = build_dependency_graph(g)
    r = sort_gadget(depgraph, name)
    #remove duplicated state setting gadgets 
    src = g[0]
    print "%s: Start from %s" % ("depgraph_%s" % name, src.asm)
    des = networkx.dag.descendants(depgraph, src)
    r = [x for x in r if (x in des or x == src)]
    sort += r
    return sort

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
    #.testcase start at 0x00214000 in base state kernel
    if DEBUG >= 3:
        cmdline = "readelf --relocs %s" % tmpobj
        subprocess.call(cmdline.split())
    cmdline = "ld -m elf_i386 -Ttext 0x214000 -o %s %s" % (tmpelf, tmpobj)
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
def gen_floppy_with_testcase(testcase, kernel = None, floppy = None, mode = 0):
    global count_addr
    global MODE
    global next_addr
    global start_addr
    global end_addr
    global PG
    
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
        revert = [] # Undo init state
        revert_ = [] # A copy of revert; regenerate instead of copy because patch ljmp
        done = set()
        
        # Generate code for initializing registers and memory locations
        for rm in regs + memlocs:
            orig_value = rm.in_snapshot(snapshot)
            if orig_value != rm.value:
                param += rm.gen_gadget(snapshot)
                revert += rm.gen_revert_gadget(snapshot)
                revert_ += rm.gen_revert_gadget(snapshot)
                done.add(rm)

        param = make_stable(param, done, snapshot)
        revert = make_stable(revert, done, snapshot)
        revert_ = make_stable(revert_, done, snapshot)
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

        (backup, set_r, copy_r, setinput, code, output, restore) \
                = Gadget.gen_root(snapshot, shellcode, count)
        asm = "push %eax;"
        copy_r = [Gadget(asm = asm, mnemonic = "")] + copy_r
        asm = "pop %eax;"
        copy_r += [Gadget(asm = asm, mnemonic = "")]
        asm = "jmp forward_%.8x;" % l2 # jump over revert' and execute post
        for g in copy_r:
            g.kill -= set([Register("EAX")])
        code += [Gadget(asm = asm, mnemonic = "jump to post")]

        # Copy initial inputs of 1st testcase to R block
        if count == 1:
            startup += set_r
        
        #jump to TC beginning for a fixed # of times                   
        asm = "";
        if MODE > 2:
            asm = "decl 0x%x; " \
                "jnz forward_%.8x; // back to loop entrance" % (count_addr, ls)
        loop = [Gadget(asm = asm, mnemonic = "loop")] 

        if MODE <= 0:
            revert_ = [];
            revert = [];
                       
        # Sort gadgets & add labels to return points
        asm = "movl $forward_%.8x,0x%x;" % (l2, retp)
        setinput = [Gadget(asm = asm, mnemonic = "return to post")] + setinput
        depgraph = build_dependency_graph(setinput)
        setinput = sort_gadget(depgraph, setinput)

        pre = [merge_glist(backup, "backup"), merge_glist(copy_r, "copy R blocks"), \
                merge_glist(setinput, "R 2 input")]        
        pre = remove_none(param + pre)        
        depgraph = build_dependency_graph(pre)
        pre = sort_gadget(depgraph, pre)
        pre = [Gadget(asm = "forward_%.8x:" % ls, mnemonic = "loop start point")] + pre

        post = output + restore
        depgraph = build_dependency_graph(post)
        post = sort_gadget(depgraph, post)
        depgraph = build_dependency_graph(revert)
        revert = sort_gadget(depgraph, revert)
        depgraph = build_dependency_graph(revert_)
        revert_ = sort_gadget(depgraph, revert_)

        asm = "movl $forward_%.8x,0x%x;" % (l1, retp)
        code = [Gadget(asm = asm, mnemonic = "return to revert_")] + code
        asm = "movl $forward_%.8x,0x%x;" % (l2, retp)
        revert_ = [Gadget(asm = asm, mnemonic = "return to post")] + revert_
        asm = "movl $forward_%.8x,0x%x;" % (l3, retp)
        post = [Gadget(asm = asm, mnemonic = "return to revert")] + post
        asm = "movl $forward_%.8x,0x%x;" % (l4, retp)
        revert = [Gadget(asm = asm, mnemonic = "return to loop")] + revert
        asm = "movl $forward_%.8x,0x%x;" % (l5, retp)
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

    opts = {"testcase" : None, "kernel" : None, "floppy" : None, "mode" : 0}
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
