#!/usr/bin/env python

import os
from os.path import dirname, basename, abspath, join as joinpath, isfile
import sys
import struct
import random
import subprocess
import time
import tempfile as tempfile_
import networkx
import elf
import StringIO
import hashlib
import cpustate_x86
from common import *
from numpy.f2py.f2py_testing import cmdline
from telnetlib import theNULL
import binascii

ROOT = abspath(joinpath(dirname(abspath(__file__)), ".."))
KERNEL = joinpath(ROOT, "kernel")
GRUB = joinpath(ROOT, "grub_stuff")
GRUB_EXE = joinpath(ROOT, "scripts/grub")
SNAPSHOT = joinpath(ROOT, "base.snap")
TESTCASE = ".testcase"
NULL = open("/dev/null", "w")
FLOPPY_TEMPLATE = "/tmp/gen-floppy-image.template"
DEBUG = 0

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
# Given an hex, return corresponding mask so that all non zero bytes are 
# masked off
# ===-------------------------------------------------------------------===    
def get_mask(value):
    i = 0
    div = 0x1000000
    mask = 0x0
    while div != 0:
        if value/div == 0:
            mask += 0xff
        value =value % div
        i = i + 1
        div = div / 0x100
        if div != 0:
            mask = mask * 0x100
    return mask

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


class SegmentRegister(Register):
    def __init__(self, name, value = None):
        Register.__init__(self, name, value, size = 16)

    def gen_gadget(self, snapshot):
        return Gadget.gen_set_sreg(self, snapshot)
        
    def in_snapshot(self, snapshot):
        return in_snapshot_sreg(self.name, snapshot)


class ControlRegister(Register):
    def __init__(self, name, value = None):
        Register.__init__(self, name, value)

    def in_snapshot(self, snapshot):
        return in_snapshot_creg(self.name, snapshot)

    def gen_gadget(self, snapshot):
        return Gadget.gen_set_creg(self, snapshot)
        

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


    def __repr__(self):
        return self.mnemonic

    # ===-------------------------------------------------------------------===
    # Return true if any of the followings is true:
    # * g1 defines what g0 kills 
    # * g0 uses what g1 defines
    # * g0 use what g1 affects
    # ===-------------------------------------------------------------------===
    def depend(g1, g0):
        return (g1.define & g0.kill) or \
            (g0.use & g1.define or "*" in g1.define) or \
            (g1.affect & g0.use)

    # ===-------------------------------------------------------------------===
    # Generate a gadget to set a register
    # ===-------------------------------------------------------------------===
    @staticmethod
    def gen_set_reg(reg, snapshot):
        asm = "nop; // %s" % (reg.name.lower())
        define, kill, use = [reg], [], []

        if reg.name == "EFLAGS":
            asm = "push $0x%.8x; popf; // eflags" % (reg.value)
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
                        define = define + ["patch_ljmp_target", "*"], 
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
        define, kill, use = [reg], [Register("EAX")], []
        asm = "mov $0x%.8x, %%eax; mov %%eax,%%%s; // %s" % \
            (reg.value, reg.name.lower(), reg.name.lower())
#         mask = get_mask(reg.value) 
#         asm = "mov %%%s,%%eax;" \
#             "and $0x%.8x,%%eax;" \
#             "or $0x%.8x,%%eax;" \
#             "mov %%eax, %%%s;//%s" % (reg.name.lower(), mask, reg.value, reg.name.lower(), reg.name.lower())
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


    # ===-------------------------------------------------------------------===
    # Generate a gadget to run the shellocde (i.e., the real testcase)
    # ===-------------------------------------------------------------------===
    @staticmethod
    def gen_shellcode(snapshot, shellcode, aggreg = 0):
        r = random.randint(0, 0xffffffff)
        x = ",".join("0x%.2x" % ord(b) for b in shellcode)
        insn = disasm(shellcode)[0]
        f = Tempfile()
        f.write(shellcode)
        p = subprocess.Popen(["objdump", "-b", "binary", "-m", "i386", "-EL", "-D", "%s" % f], 
                             stdin=subprocess.PIPE, 
                             stdout=subprocess.PIPE)
        s = p.communicate()[0]
        print "s = %s\n" % s
        s = s.split('\n')[-2]
        print "s = %s\n" % s
        dest = s.split()[-1]
        str = s.split('\t')[2]
        print "str = %s\n" % str
        
        #remove prefixs
        while str.split()[0] in prefix:
            str = ' '.join(str.split()[1:])
        
        print "after stripping: %s\n" % str
        op = str.split()[0].strip()
        args = "<no operand>"
        n = 0
        print "len: %d\n" % len(str.split())
        if len(str.split()) > 1:
            args = str.split()[1]
            n = len(args.split(","))
        
        if parentheses(args):
            f = False
            for arg in args.split(","):
                if parentheses(arg):
                    f = True
                    break
            if f == False:
                n = 1
        print "operation = %s, operands = %s\n" % (op, args)
        print "There are %d operands\n" % n
        
        ignore = ["vmcall",
                  "vmoff",
                  "vmresume",
                  "vmxoff"
                  "vmread",
                  "vmwrite",
                  "wbinvd",
                  "pause",
                  "lfence",
                  "mfence",
                  "sfence",
                  "ud1",
                  "nop"]
        
        tc = "jmp forward_%.8x;forward_%.8x: " \
            ".byte %s;// shellcode: %s" % (r, r, x, insn) 
        gtc = Gadget(asm = tc, mnemonic = "shellcode")
        
        # Map virtual page 0 to a higher physical page
        deref4 = lambda x: deref(x, 0, 4)
        cr0 = in_snapshot_creg("CR0", snapshot)
        cr3 = in_snapshot_creg("CR3", snapshot) & 0xfffff000
        pde0 = in_snapshot_mem((cr3, 4), snapshot)
        print "gen_prologue: pde0 = #%s#\n" % pde0
        pte0 = in_snapshot_mem((deref4(pde0) & 0xfffff000, 4), snapshot)
        pte1022 = in_snapshot_mem((((deref4(pde0) & 0xfffff000) + 1022*4), 4), 
                                  snapshot)
        newpte0 = (deref4(pte0) & 0xfff) | (deref4(pte1022) & 0xfffff000)
        rs = "mov $0x%.8x,%%eax; mov %%eax,%%cr0; " \
            "movl $0x%s,0x%.8x; " \
            "movl $0x%.8x,0x%.8x; // rebase page 0" % \
            (cr0, binascii.hexlify(pde0[::-1]), cr3 ,newpte0, deref4(pde0) & 0xfffff000)
        grs = Gadget(asm = rs, mnemonic = "rebase page 0")      
        
        if int(aggreg) == 0:
            #Generate non-aggregate testcase
            return [grs, gtc]
        else:
            if n == 0:
                if op in ignore:
                    return [grs, gtc]
                elif op in ["clc", "cli", "rsm"]:
                    #eflags only
                    r1 = random.randint(0x00218008, 0x003fffff)
                    asm = "pushf; " \
                        "pop 0x%x; " \
                        "popf;//store and reset flag register" % r1
                    g = Gadget(asm = asm, mnemonic = "shellcode")
                    return [grs. gtc, g]
                elif op in ["pushf"]:
                    r1 = random.randint(0x00218008, 0x003fffff)
                    asm = "pop 0x%x;" % r1
                    g = Gadget(asm = asm, mnemonic = "shellcode")
                    return [grs, gtc, g]
                elif op in ["lahf"]:
                    #eax only
                    r1 = random.randint(0x00218008, 0x003fffff)
                    asm = "mov %%eax,0x%x;//store eax" % r1
                    g = Gadget(asm = asm, mnemonic = "shellcode")
                    return [grs, gtc, g]
                elif op in ["xsetbv"]:
                    #CRX, X = {0, 2, 3, 4}
                    r1 = random.randint(0x00218008, 0x003fffff)
                    r2 = random.randint(0x00218008, 0x003fffff)
                    r3 = random.randint(0x00218008, 0x003fffff)
                    r4 = random.randint(0x00218008, 0x003fffff)
                    asm = "mov %%cr0,%%eax;" \
                        "mov %%eax,0x%x;" \
                        "mov %%cr2,%%eax;" \
                        "mov %%eax,0x%x;" \
                        "mov %%cr3,%%eax;" \
                        "mov %%eax,0x%x;" \
                        "mov %%cr4,%%eax;" \
                        "mov %%eax,0x%x;//store CRX" % (r1, r2, r3, r4)
                    g = Gadget(asm = asm, mnemonic = "shellcode")
                    return [grs, gtc, g]
                elif op in ["xgetbv", "rdmsr", "rdtsc", "cbtw", "cwtl", "cwtd"]:
                    #eax, edx
                    r1 = random.randint(0x00218008, 0x003fffff)
                    r2 = random.randint(0x00218008, 0x003fffff)                    
                    asm = "mov %%eax,0x%x;" \
                        "mov %%edx,0x%x;" % (r1, r2)
                    g = Gadget(asm = asm, mnemonic = "shellcode")
                    return [grs, gtc, g]
                elif op in ["sysexit", "sysenter", "ret", "lret"]:
                    #esp, eip, cs, ss
                    #Currently doesn't work since those instructions change control flow
                    l = random.randint(0, 0xffffffff)
                    r1 = random.randint(0x00218008, 0x003fffff)
                    r2 = random.randint(0x00218008, 0x003fffff)
                    r3 = random.randint(0x00218008, 0x003fffff)
                    r4 = random.randint(0x00218008, 0x003fffff)
                    asm1 = "mov %%esp,0x%x;" \
                        "mov %%cs,0x%x;" \
                        "mov %%ss,0x%x;// store esp, cs, and ss" % (r1, r2, r3)
                    asm2 = "call forward_%.8x;forward_%.8x:" \
                        "pop 0x%x;//store eip" % (l, l, r4)
                    g1 = Gadget(asm = asm1, mnemonic = "shellcode")
                    g2 = Gadget(asm = asm2, mnemonic = "shellcode")
                    return [grs, gtc, g1, g2]
                elif op in ["daa", "das", "aaa", "aad", "aam", "aas"]:
                    #eax, eflags
                    r1 = random.randint(0x00218008, 0x003fffff)
                    r2 = random.randint(0x00218008, 0x003fffff)
                    asm1 = "mov %%eax,0x%x;//store eax" % r1                
                    asm2 = "pushf; " \
                        "pop 0x%x; " \
                        "popf;//store and reset flag register" % r2
                    g1 = Gadget(asm = asm1, mnemonic = "shellcode")
                    g2 = Gadget(asm = asm2, mnemonic = "shellcode")   
                    return [grs, gtc, g1, g2]                 
                else:
                    print "%s: Unsupported 0-op instruction\n" % op
                    sys.exit(1)
            else:
                if op == "call" and n == 1:
                    r1 = random.randint(0, 0xffffffff)
                    r2 = random.randint(0, 0xffffffff)
                    fp = random.randint(0x00218008, 0x003fffff)
                    faddr = random.randint(0x00218008, 0x003fffff)
                    asm1 = ""
                    print "pos of *: %d\n" % args.find("*")
                    if args.find("*") == 0:
                        if parentheses(args):
                            #Call_EdM/EwM
                            asm1 = "mov $forward_%.8x,%%eax;" \
                                "mov %%eax, 0x%x;"\
                                "mov $0x%x,%%eax;" % (r2, fp, fp)
                        else:
                            #Call_EdR/EwR
                            asm1 = "mov $forward_%.8x,%%eax;" % r2
                    else:
                        #Call_Jd/Jw
                        #call label also work
                        asm1 = "mov $forward_%.8x,%%eax;" \
                            "mov %%eax,%s;" % (r2, args)       
                    asm2 = "forward_%.8x: jmp forward_%.8x; //call target" % (r2, r1)
                    asm3 = "forward_%.8x: pushf; " \
                        "pop 0x%x; " \
                        "popf;//store and reset flag register" % (r1, faddr)  
                    g1 = Gadget(asm = asm1, mnemonic = "shellcode")
                    g2 = Gadget(asm = asm2, mnemonic = "shellcode")
                    g3 = Gadget(asm = asm3, mnemonic = "shellcode")    
                    return [grs, g1, gtc, g2, g3]
                else:
                    #Normal insns
                    if n > 1:
                        dest = dest.split(",")[-1]
                    print "destination: %s #####################" % dest
                    addr = random.randint(0x00218008, 0x003fffff)   
                    faddr = random.randint(0x00218008, 0x003fffff)     
                    asm1 = "mov %s,%%eax; " \
                        "mov %%eax,0x%x; " \
                        "xor %%eax,%%eax; " \
                        "mov %%eax,%s;//store and reset destination" % (dest, addr, dest)
                    asm2 = "pushf; " \
                        "pop 0x%x; " \
                        "popf;//store and reset flag register" % (faddr)
                    g1 = Gadget(asm = asm1, mnemonic = "shellcode")
                    g2 = Gadget(asm = asm2, mnemonic = "shellcode")    
                    return [grs, gtc, g1, g2]


    @staticmethod
    def gen_prologue(snapshot, aggreg = 0):
        asm = ""
        if int(aggreg) != 0:
            asm += "pushf; " 
        asm += "invlpg 0x0;" 
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
        for g1 in gadgets:
            if g1 != g0 and g1.depend(g0):
                dg.add_edge(g0, g1)

    return dg


# ===-----------------------------------------------------------------------===
# Return the dependency graph in Graphviz format
# ===-----------------------------------------------------------------------===
def dot_dependency_graph(graph):
    r = "digraph G {"
    for n in graph:
        r += "%u [label=\"%s\"];\n" % (id(n), n.mnemonic)

    for n in graph:
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
                    if n in seen: return #CYCLE !!
                    new_nodes.append(n)
            if new_nodes:   # Add new_nodes to fringe
                fringe.extend(new_nodes)
            else:           # No new nodes so w is fully explored
                explored[w]=1
                order_explored.insert(0,w) # reverse order explored
                fringe.pop()    # done considering this node
    
    return order_explored


# ===-----------------------------------------------------------------------===
# Compile a sequence of gadgets into x86 code
# ===-----------------------------------------------------------------------===
def compile_gadgets(gadget, directive = ""):
    # Build a graph representing dependencies among gadgets and order the
    # gadgets to make sure all dependencies are satisfied
    code = "";
    for tuple in gadget:
        (prologue, body, epilogue) = tuple;
        depgraph = build_dependency_graph(body)
        if DEBUG >= 2:
            open("/tmp/depgraph.dot", "w").write(dot_dependency_graph(depgraph))
    
        body = topological_sort(depgraph)
    
        # Generate the assembly code
        i = 0
        for g in prologue + body + epilogue:
            code += "%s\n" % (g.asm)
            if i and i % 8 == 0:
                r = random.randint(0, 0xffffffff)
                code += "jmp forward_%.8x; forward_%.8x:\n" % (r, r)
            i += 1

    # Assemble
    tmpobj = Tempfile()
    tmpelf = Tempfile()
    cmdline = "as -32 -o %s -" % tmpobj
    p = subprocess.Popen(cmdline.split(), 
                         stdin = subprocess.PIPE, 
                         stdout = subprocess.PIPE, 
                         stderr = subprocess.PIPE)
    prog = str("\n.text\n" + directive + "\n" + code + "\n")
    stdout, stderr = p.communicate(prog)
    if stderr != "":
        print "[E] Can't compile code:\n%s\n-%s-" % (prog, stderr)
        exit(1)
        
    #For correct direct jump location, use linker
    #.testcase start at 0x00214000 in base state kernel
    cmdline = "ld -m elf_i386 -Ttext 0x214000 -o %s %s" % (tmpelf, tmpobj)
    subprocess.call(cmdline.split())

    # Extract the code of the gadgets (.text section) from the elf object
    cmdline = "objcopy -O binary -j .text %s" % str(tmpelf)
    print "cmdlind: %s\n" % cmdline
    subprocess.call(cmdline.split())
    obj = open(str(tmpelf)).read()

    return code, obj


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

    cmd = """mcopy -i %s %s ::kernel && mcopy -i %s %s ::kernel.md5 && mcopy -i %s %s ::testcase.md5""" % \
        (floppy, kernel, floppy, cksum, floppy, testcase)
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
def gen_floppy_with_testcase(testcase, aggreg = 0, kernel = None, floppy = None):
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
    
        body = []
        done = set()
        
        # Generate code for initializing registers and memory locations
        for rm in regs + memlocs:
            orig_value = rm.in_snapshot(snapshot)
            if orig_value != rm.value:
                body += rm.gen_gadget(snapshot)
                done.add(rm)
            
        # Need one or more extra passes to define what has been killed but not
        # defined
        stable = False
        while not stable:
            stable = True
    
            killed = set()
            defined = set()
            for g in body:
                killed |= g.kill
                defined |= g.define
    
            if len(killed - defined):
                print "Forcing gadgets for: ", \
                    ", ".join([str(v) for v in killed - defined])
    
            for rm in killed - defined:
                assert rm not in done
                stable = False
                rm.value = rm.in_snapshot(snapshot)
                body += rm.gen_gadget(snapshot)
    
    
        prologue = Gadget.gen_prologue(snapshot, aggreg)
        epilogue = Gadget.gen_shellcode(snapshot, shellcode, aggreg);
        if count == num:
            epilogue = epilogue + Gadget.gen_end_testcase()
            
        gadget.append((prologue, body, epilogue))
    
        if DEBUG >= 1:
            for g in prologue + body + epilogue:
                print
                print g

    code, obj = compile_gadgets(gadget)

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

    opts = {"testcase" : None, "aggreg" : 0, "kernel" : None, "floppy" : None}
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
