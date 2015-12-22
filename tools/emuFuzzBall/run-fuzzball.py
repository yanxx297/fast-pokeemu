#!/usr/bin/python

import os, sys, subprocess, base64, time

t0 = time.time()

HOME = os.getenv("HOME")
CHROOT = "" # "dchroot -d -c karmic-x86 --"
FUZZBALL = os.path.join(os.path.dirname(__file__), "./emu_fuzzball")
cmdline = sys.argv[1:]
# SOLVER = "-stp-path /usr/bin/stp"
SOLVER = "-solver z3vc"
OUTDIR = os.getenv("FUZZBALL_OUTDIR", 
                   "/tmp/fuzzball-%s-output" % os.path.basename(cmdline[0]))
FUZZBALL_ENV_ARGS = os.getenv("FUZZBALL_ARGS", "")
FUZZBALL_MAX_ITERS = os.getenv("FUZZBALL_MAX_ITERATIONS", "1879048191")
FUZZBALL_ARGS = " -linux-syscalls -trace-iterations -paths-limit %s -output-dir %s %s %s" % \
    (FUZZBALL_MAX_ITERS, OUTDIR, SOLVER, FUZZBALL_ENV_ARGS)
FUZZBALL_COREDUMP_ADDR = None
corefile = None

def encode(s):
    s = base64.b32encode(s)
    # We replace the default padding base32 padding '=' with 'z' because '=' is
    # not allowed by Vine in a variable name
    return s.replace("=", "z")

def terminal_size():
    import fcntl, termios, struct

    in_ = struct.pack('HHHH', 0, 0, 0, 0)
    out = fcntl.ioctl(0, termios.TIOCGWINSZ, in_)
    h, w, hp, wp = struct.unpack('HHHH', out)
    return w, h

def columns(): 
    return terminal_size()[0]

try:
    os.mkdir(OUTDIR)
except OSError:
    pass

start_address = None
ignore_paths = []
symbolic_variables = {}
asserts = []
args = []

cpu_regs = []

# perform a dry run to build the command line arguments
env = os.environ.copy()
env["FUZZBALL_DRY_RUN"] = "1"
print " ".join(cmdline)
p = subprocess.Popen(cmdline, stdout = subprocess.PIPE, env = env)
out, err = p.communicate()
assert p.wait() == 0, "%s %s\n" % (str(p.returncode), err)
if os.getenv("FUZZBALL_DRY_RUN_DEBUG", False):
    print "#"*columns()
    print out,

for l in out.split("\n"):
    if l.startswith("FUZZBALL_SYMBOLIC_VARIABLE"):
        l = l.split("\t")[1:]
        a, s, n = int(l[0], 16), int(l[1]), l[2]
        n = n.split()
        for i in range(s):
            n_ = ""
            if len(n) > 1:
                n_ = " ".join(n[1:])
            n_ = "in_%s_%s_%u_%u" % (n[0], encode(n_), s, i)
            symbolic_variables[a + i] = (n_, 1)
            args += ["-symbolic-byte", "0x%.8x=%s" % (a + i, n_)]
    elif l.startswith("FUZZBALL_START_ADDRESS"):
        addr = int(l.split("\t")[1], 16)
        start_address = int(addr)
        args += ["-fuzz-start-addr", "0x%.8x" % addr]
    elif l.startswith("FUZZBALL_STOP_ADDRESS"):
        addr = int(l.split("\t")[1], 16)
        start_address = int(addr)
        args += ["-simulate-exit", "0x%.8x" % addr]
    elif l.startswith("FUZZBALL_IGNORE_PATH_THROUGH"):
        addr = int(l.split("\t")[1], 16)
        ignore_paths += [addr]
        args += ["-ignore-path", "0x%.8x" % addr]
    elif l.startswith("FUZZBALL_ASSERT_EQ"):
        l = l.split("\t")[1:]
        a, m, v = int(l[0], 16), int(l[1], 16), int(l[2], 16)
        asserts += [("=", a, m, v)]
    elif l.startswith("FUZZBALL_COREDUMP_ADDRESS"):
        addr = int(l.split("\t")[1], 16)
        FUZZBALL_COREDUMP_ADDR = addr
    elif l.startswith("FUZZBALL_CONCRETIZE_VARIABLE"):
        l = l.split("\t")[1:]
        a, e, v = int(l[0], 16), l[1], l[2]
        args += ["-concretize-expr", "0x%.8x#%s#%s" % (a, e, v)]

    # elif l.startswith("FUZZBALL_REG"):
    #     l = l.split("\t")[1:]
    #     r, s, a = l[0], int(l[1]), int(l[2], 16)
    #     cpu_regs += [(r, s, a)]
    #     args += ["-cpu-reg", "%s:%d:0x%.8x" % (r, s, a)]

    # elif l.startswith("FUZZBALL_MEM"):
    #     l = l.split("\t")[1:]
    #     s, a = int(l[1]), int(l[0], 16)
    #     phys_mem = (r, a)
    #     args += ["-phys-mem", "0x%.8x:0x%.8x" % (a, a + s - 1)]


# This is postponed to make sure we can resolve all addresses
for t, a, m, v in asserts:
    assert a in symbolic_variables, \
        "%.8x is not mapped to any symbolic variables" % a
    i = symbolic_variables[a]

    if t == "=":
        if m ==  255:
            args += ["-extra-condition", "(%s == %u:reg8_t)" % (i[0], v)]
        else:
            args += ["-extra-condition", "((%s & %u:reg8_t) == %u:reg8_t)" % \
                         (i[0], m, v)]
    else:
        assert 0

print "Dry run completed in %.3fs\n" % (time.time() - t0)


aaaa = symbolic_variables.items()
aaaa.sort(lambda x, y: cmp(x[0], y[0]))
f = open("/tmp/f.s", "w")
for a, v in aaaa:
    print >> f, a, v

cmdline = CHROOT.split() + FUZZBALL.split() + FUZZBALL_ARGS.split() + \
    args + [cmdline[0]] + ["--"] + cmdline

cmdline_ = " ".join(cmdline)
if len(cmdline_) >= 256:
    cmdline_ = cmdline_[:256] + "..."

print "%d symbolic bytes" % len(symbolic_variables)
print cmdline_
print "#"*columns()
print

open("/tmp/fuzzball.cmd", "w").write(" ".join(["\"%s\"" % c for c in cmdline]))

env = os.environ.copy()
env["FUZZBALL_EXECUTION"] = "1"
subprocess.call(cmdline, env = env)

try:
    os.rmdir("./fuzzball-tmp-1")
except OSError:
    pass

print "Run completed in %.3fs" % (time.time() - t0)
