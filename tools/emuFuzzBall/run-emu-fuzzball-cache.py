#!/usr/bin/python

import os, sys, subprocess, base64, time
from cpustate_x86 import *
from common import *

t0 = time.time()

HOME = os.getenv("HOME")
HERE = os.path.abspath(os.path.dirname(__file__))
DEBUG = os.getenv("FUZZBALL_DEBUG", False)
if not DEBUG:
    FUZZBALL = os.path.join(HERE, "emu_fuzzball")
else:
    os.environ["OCAMLRUNPARAM"] = "b"
    FUZZBALL = os.path.join(HERE, "emu_fuzzball.dbg")

#GDB = os.path.join(HERE, "gdb")
GDB = "gdb"
OUTDIR = os.getenv("FUZZBALL_OUTDIR", "/tmp/fuzzball-output")
FUZZBALL_ENV_ARGS = os.getenv("FUZZBALL_ARGS", "")
FUZZBALL_MAX_ITERS = os.getenv("FUZZBALL_MAX_ITERATIONS", "4096")
FUZZBALL_ARGS = "-solver z3vc -linux-syscalls -trace-iterations " \
    "-paths-limit %s -output-dir %s %s" % \
    (FUZZBALL_MAX_ITERS, OUTDIR, FUZZBALL_ENV_ARGS)

usrcmdline = sys.argv[1:]

corefile = Tempfile(suffix = ".core")

symbolic_regs = True
symbolic_sregs = True
symbolic_cregs = False
symbolic_dregs = False
symbolic_gdt = True
symbolic_idt = False
symbolic_pt = False
stop_at_exceptions = True
ignored_functions = [] # ["fprintf"]
symbolic_mem_regions = [(0x1000, 16, "PAGEONE"), (0x2000, 16, "PAGETWO")]

start_address = None
start_tracing_address = None
coredump_address = None
stop_addresses = []
ignore_paths = []

emulator = None
cpu_regs = []
gdtr = None
idtr = None
tr = None
ldtr = None
phys_mem = None
exception = None
exception_handlers = []
read_virt_mem_handlers = []
write_virt_mem_handlers = []
fpu = None
shellcode = None
snapshot = None
snapshot_file = None
snapshot_md5 = None
ignored_calls = []
get_tls = None
tls_base = None
ignore_pathcond_till = None
scratchpad = None
msrs = None
descriptor_cache = None

cmdline = []

symbolic_bytes = []
concrete_bytes = []


def extra_cond_eq(n, v, m = 0xff):
    if m == 0xff:
        return ["-extra-condition", "(%s == %u:reg8_t)" % (n, v)]
    elif m != 0:
        return ["-extra-condition", 
                "((%s & %u:reg8_t) == %u:reg8_t)" % (n, m, v & m)]
    else:
        return []


def vine_for_mem(a):
    return "mem[0x%.8x:reg32_t]:reg32_t" % a


def vine_for_stack(s):
    return "mem[R_ESP:reg32_t + %d:reg32_t]:reg32_t" % (s * 4)


def addr_for_symbolic_bit():
    global scratchpad
    a, s, u = scratchpad
    assert u < s
    scratchpad = (a, s, u + 1)
    return a + s - u


# ===-----------------------------------------------------------------------===
# Build cmdline arguments for making a memory location symbolic (bits set in
# the mask are asserted to make them concrete)
# ===-----------------------------------------------------------------------===
def __make_mem_symbolic(haddr, gaddr, sym, value = 0, mask = 0, mindist = False):
    global symbolic_bytes, concrete_bytes

    cmdline = []

    if mask == 0:
        # all bits are symbolic
        name = "%s" % (sym)
        cmdline = ["-symbolic-byte", "0x%.8x=%s" % (haddr, name)]
        symbolic_bytes += [haddr]

    elif mask < 0xff:
        # some bits are symbolic, create a dummy 1-byte variable for each bit
        # and build an expression by oring concrete bits with these symbolic
        # variables

        # # concrete bits
        # cbits = 0
        # # expression for symbolic bits
        # sbits = ""

        # for b in range(8):
        #     if not mask & (1 << b):
        #         # make bit symbolic
        #         name = "in_bmem_%.8x_%s_8_%d" % (gaddr, encode(sym), b)
        #         bitaddr = addr_for_symbolic_bit()
        #         cmdline += ["-symbolic-byte", "0x%.8x=%s" % (bitaddr, name)]

        #         sbits_ = "(%s & %d:reg8_t)" % (name, 1 << b)
        #         if not sbits:
        #             sbits = sbits_
        #         else:
        #             sbits = "(%s | %s)" % (sbits, sbits_)
        #     else:
        #         # make bit concrete
        #         print repr(value)
        #         cbits |= value & (1 << b)
            
        # # build expression for the byte
        # cmdline += ["-symbolic-byte-expr", 
        #             "0x%.8x#(%s | 0x%x:reg8_t)" % (haddr, sbits, cbits)] 

        name = "%s" % (sym)
        cmdline = ["-symbolic-byte", "0x%.8x=%s" % (haddr, name)]
        symbolic_bytes += [haddr]
        cmdline += ["-extra-condition", "(%s & %u:reg8_t) == %u:reg8_t" % (name, mask, value & mask)]
        if mindist:
            cmdline += ["-preferred-value", "%s:0x%.2x" % (name, value)]
            
    else:
        concrete_bytes += [haddr]

    return cmdline


def make_mem_symbolic(haddr, gaddr, sym, values, masks, mindist = False):
    global symbolic_bytes, concrete_bytes

    cmdline = []

    assert len(values) == len(masks)

    for i in range(len(values)):
        cmdline += __make_mem_symbolic(haddr + i, gaddr + i, sym + "_%d" % i, 
                                       ord(values[i]), masks[i], mindist)

    return cmdline


def make_mem_concrete(haddr, size):
    global symbolic_bytes, concrete_bytes

    cmdline = []

    for i in range(size):
        concrete_bytes += [haddr + i]

    return cmdline

# ===-----------------------------------------------------------------------===
# Build cmdline arguments for making a register symbolic (bits set in the mask
# are asserted to make them concrete)
# ===-----------------------------------------------------------------------===
def make_reg_symbolic(haddr, name, size, value = 0, mask = 0):
    global symbolic_bytes, concrete_bytes

    cmdline = []
    value = chunk(value, size)[0]
    mask = chunk(mask, size)[0]

    for i in range(size):
        n = "in_%s__%d_%d" % (name, size, i)
        m, v = mask[i], value[i]
        if m < 0xff:
            cmdline += ["-symbolic-byte", "0x%.8x=%s" % (haddr + i, n)]
            symbolic_bytes += [haddr + i]
            if m > 0:
                cmdline += ["-extra-condition", 
                            "((%s & %u:reg8_t) == %u:reg8_t)" % (n, m, v & m)]
        else:
            concrete_bytes += [haddr + i]
    
    return cmdline


os.environ["COLUMNS"] = str(columns())
title = "%s" % " ".join(usrcmdline)
pad = "#"*((columns() - len(title)) / 2 - 1)
print pad + " " + title + " " + pad

# ===-----------------------------------------------------------------------===
# perform a dry run to build the command line arguments
# ===-----------------------------------------------------------------------===
env = os.environ.copy()
env["FUZZBALL_DRY_RUN"] = "1"
t1 = time.time()
print "Performing dry run...",
sys.stdout.flush()
p = subprocess.Popen(usrcmdline, stdout = subprocess.PIPE, env = env)
out, err = p.communicate()
assert p.wait() == 0, "%s %s\n" % (str(p.returncode), err)
if os.getenv("FUZZBALL_DRY_RUN_DEBUG", False):
    print "#"*columns()
    print out,
print "done (%.3fs)" % (time.time() - t1)

# ===-----------------------------------------------------------------------===
# parse the output produced by the dry run
# ===-----------------------------------------------------------------------===
for l in out.split("\n"):
    # if l.startswith("FUZZBALL_SYMBOLIC_VARIABLE"):
    #     print l
    if l.startswith("FUZZBALL_START_ADDRESS"):
        addr = int(l.split("\t")[1], 16)
        start_address = addr

    elif l.startswith("FUZZBALL_IGNORE_PATHCOND_TILL"):
        addr = int(l.split("\t")[1], 16)
        ignore_pathcond_till = addr

    elif l.startswith("FUZZBALL_START_TRACING"):
        addr = int(l.split("\t")[1], 16)
        start_tracing_address = addr

    elif l.startswith("FUZZBALL_GET_TLS"):
        addr = int(l.split("\t")[1], 16)
        get_tls = addr

    elif l.startswith("FUZZBALL_COREDUMP_ADDRESS"):
        addr = int(l.split("\t")[1], 16)
        coredump_address = addr

    elif l.startswith("FUZZBALL_DESCRIPTOR"):
        l = l.split("\t")[1:]
        descriptor_cache = (l[0], int(l[1], 16), int(l[2]))

    elif l.startswith("FUZZBALL_STOP_ADDRESS"):
        addr = int(l.split("\t")[1], 16)
        stop_addresses += [addr]

    elif l.startswith("FUZZBALL_IGNORE_PATH_THROUGH"):
        addr = int(l.split("\t")[1], 16)
        ignore_paths += [addr]

    elif l.startswith("FUZZBALL_EMULATOR"):
        l = l.split("\t")[1:]
        emulator = l[0]

    elif l.startswith("FUZZBALL_REG"):
        l = l.split("\t")[1:]
        r, s, a = l[0], int(l[1]), int(l[2], 16)
        cpu_regs += [(r, s, a)]
        
    elif l.startswith("FUZZBALL_MEM"):
        l = l.split("\t")[1:]
        s, a = int(l[1]), int(l[0], 16)
        phys_mem = (a, s)

    elif l.startswith("FUZZBALL_GDTR"):
        l = l.split("\t")[1:]
        a0, s0, a1, s1 = int(l[1], 16), int(l[0]), int(l[3], 16), int(l[2])
        gdtr = (a0, s0, a1, s1)

    elif l.startswith("FUZZBALL_IDTR"):
        l = l.split("\t")[1:]
        a0, s0, a1, s1 = int(l[1], 16), int(l[0]), int(l[3], 16), int(l[2])
        idtr = (a0, s0, a1, s1)

    elif l.startswith("FUZZBALL_TR"):
        l = l.split("\t")[1:]
        a0, s0 = int(l[1], 16), int(l[0])
        tr = (a0, s0)

    elif l.startswith("FUZZBALL_LDTR"):
        l = l.split("\t")[1:]
        a0, s0 = int(l[1], 16), int(l[0])
        ldtr = (a0, s0)

    elif l.startswith("FUZZBALL_MEM"):
        l = l.split("\t")[1:]
        s, a = int(l[1]), int(l[0], 16)
        phys_mem = (a, s)

    elif l.startswith("FUZZBALL_SCRATCHPAD"):
        l = l.split("\t")[1:]
        s, a = int(l[1]), int(l[0], 16)
        scratchpad = (a, s, 0)

    elif l.startswith("FUZZBALL_FPU"):
        l = l.split("\t")[1:]
        s, a = int(l[1]), int(l[0], 16)
        fpu = (a, s)
        
    elif l.startswith("FUZZBALL_EXCEPTION_HANDLER"):
        l = l.split("\t")[1:]
        a, s = int(l[0], 16), int(l[1])
        exception_handlers += [(a, s)]
        
    elif l.startswith("FUZZBALL_EXCEPTION"):
        l = l.split("\t")[1:]
        a = int(l[0], 16)
        exception = a
        
    elif l.startswith("FUZZBALL_READ_VIRTUAL_MEM"):
        l = l.split("\t")[1:]
        a, s = int(l[0], 16), int(l[1])
        read_virt_mem_handlers += [(a, s)]
        
    elif l.startswith("FUZZBALL_WRITE_VIRTUAL_MEM"):
        l = l.split("\t")[1:]
        a, s = int(l[0], 16), int(l[1])
        write_virt_mem_handlers += [(a, s)]
        
    elif l.startswith("FUZZBALL_SNAPSHOT"):
        l = l.split("\t")[1:]
        buf = open(l[0]).read()
        snapshot = X86Dump(buf)
        snapshot_file = l[0]
        snapshot_md5 = md5(buf)

    elif l.startswith("FUZZBALL_IGNORE_CALL"):
        l = l.split("\t")[1:]
        n, a, r = l[0], int(l[1], 16), int(l[2])
        ignored_calls += [(a, r, n)]

    elif l.startswith("FUZZBALL_SHELLCODE"):
        l = l.split("\t")[1:]
        shellcode = to_bin_str(l[0])

    elif l.startswith("FUZZBALL_MSRS"):
        l = l.split("\t")[1:]
        a, s = int(l[0], 16), int(l[1])
        msrs = (a, s)

# ===-----------------------------------------------------------------------===
# generate a coredump
# ===-----------------------------------------------------------------------===
if corefile:
    t1 = time.time()
    print "Generating core dump...",
    sys.stdout.flush()

    # Generate a coredump using gdb and get the address of the TLS by calling a
    # function in the binary
    gdbout = Tempfile()
    cmd = "break *0x%x\nrun\nset logging file %s\nset logging on\n" \
        "print/x 0x%x()\nset logging off\ngenerate-core-file %s" % \
        (coredump_address, str(gdbout), get_tls, str(corefile))

    tmp = Tempfile(data = cmd)
    p = subprocess.check_call([GDB, "-q", "-batch", "-x", str(tmp), "-args"] + \
                                    usrcmdline, stdout = NULL, stderr = NULL)
    assert p == 0
    print "done (%.3fs)" % (time.time() - t1)
    
    assert corefile.read(7) == "\x7f\x45\x4c\x46\x01\x01\x01"

    # Prase the output of gdb to get the base of the TLS
    gdbout = gdbout.read()
    assert gdbout.startswith("$1 = ")
    tls_base = int(gdbout.split(" = ")[1], 16)


# ===-----------------------------------------------------------------------===
# GDT
#
# |---------------------------------------------|
# |             Segment Descriptor              |
# |---------------------------------------------|
# |33222222|2|2|2|2| 11 11 |1|11|1|11  |        |
# |10987654|3|2|1|0| 98 76 |5|43|2|1098|76543210|
# |--------|-|-|-|-|-------|-|--|-|----|--------|
# |Base    |G|D|L|A|Limit  |P|D |S|Type|Base    |
# |[31-24] | |/| |V|[19-16]| |P | |    |[23-16] |
# |        | |B| |L|       | |L | |    |        |
# |------------------------|--------------------|
# |       Base [15-0]      |    Limit [15-0]    |
# |------------------------|--------------------|
# ===-----------------------------------------------------------------------===
gdt_base = snapshot.cpus[0].sregs_state.gdtr.base
gdt_limit = snapshot.cpus[0].sregs_state.gdtr.limit
gdt_data = snapshot.mem.data[gdt_base:gdt_base+gdt_limit]
# keep limit, base, s, and g concrete
# masks = [0xff, 0xff, 0xff, 0xff, 0xff, 0x10, 0xf|0x80, 0xff]
# keep base, s, type, and g concrete
mask = [0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0, 0x0]
for i in [8]:
    data = gdt_data[i*8:(i+1)*8]
    ga = gdt_base + i*8
    ha = ga + phys_mem[0]
    cmdline += make_mem_symbolic(ha, ga, "in_desc", data, mask, True)

# ===-----------------------------------------------------------------------===
# Monitor the final state of the memory/fpu/exception
# ===-----------------------------------------------------------------------===
cmdline += ["-dump-region", "0x%.8x:%u=out_mem___1" % phys_mem]
cmdline += ["-dump-region", "0x%.8x:%u=out_desc_cache" % (descriptor_cache[1], descriptor_cache[2])]

cmdline += ["-fuzz-start-addr", "0x%.8x" % start_address]
for a in ignore_paths:
    cmdline += ["-ignore-path", "0x%.8x" % a]
for a in stop_addresses:
    cmdline += ["-symulate-exit", "0x%.8x" % a]
if ignore_pathcond_till:
    cmdline += ["-ignore-pc-till", "0x%.8x" % ignore_pathcond_till]
if start_tracing_address:
    cmdline += ["-trace-from", "0x%.8x" % start_tracing_address]


try:
    os.mkdir(OUTDIR)
except OSError:
    pass

if corefile:
    cmdline += ["-core", str(corefile)]
    cmdline += ["-tls-base", "0x%.8x" % tls_base]


cmdline = FUZZBALL.split() + FUZZBALL_ARGS.split() + cmdline + \
    [usrcmdline[0], "--"] + usrcmdline

cmdline_ = " ".join(cmdline)
if len(cmdline_) >= columns()*3:
    cmdline_ = cmdline_[:columns()*3 - 8] + "..."

print "Starting FuzzBall:", cmdline_
print "#"*columns()
print

open("/tmp/fuzzball.cmd", "w").write(" ".join(["\"%s\"" % c for c in cmdline]))

open("%s/snapshot" % OUTDIR, "w").write(snapshot_md5)
open("%s/cmdline" % OUTDIR, "w").write("\x00".join(usrcmdline))
open("%s/exe" % OUTDIR, "w").write(md5(open(usrcmdline[0])))
open("%s/shellcode" % OUTDIR, "w").write(shellcode)

r = subprocess.call(cmdline)

open("%s/exitstatus" % OUTDIR, "w").write(str(r))
open("%s/time" % OUTDIR, "w").write("%f" % (time.time() - t0))

try:
    os.rmdir("./fuzzball-tmp-1")
except OSError:
    pass

print "Run completed in %.3fs" % (time.time() - t0)
