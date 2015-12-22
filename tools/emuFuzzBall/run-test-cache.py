import os, sys, struct, subprocess, random

def run1(dword1, dword2):
    out1 = {}
    p = subprocess.Popen(["../WhiteBochs/test-cache", hex(dword1), 
                          hex(dword2)], 
                         stdout = subprocess.PIPE)
    out = p.communicate()[0]
    for l in out.split("\n"):
        if not l:
            continue
        l = l.split("=")
        out1[l[0]] = int(l[1], 16)
    return out1

def run2(dword1, dword2):
    dword1 = struct.pack("I", dword1)
    dword2 = struct.pack("I", dword2)

    cmdline = ["./multi_path_test", "-prog", "/tmp/CS.merged"]

    i = 0
    for b in dword1 + dword2:
        cmdline += ["-ctx", "in_desc_%d=0x%.2x" % (i, ord(b))]
        i += 1

    out1 = {}
    p = subprocess.Popen(cmdline, stdout = subprocess.PIPE)
    out = p.communicate()[0]
    for l in out.split("\n"):
        if not l:
            continue
        l = l.split("=")
        out1[l[0]] = int(l[1], 16)
    return out1
    
def diff(out1, out2, verbose = True):
    kk = out1.keys()
    kk.sort()

    res = True

    for k in kk:
        if k in out2:
            if out2[k] != out1[k]:
                res = False
            v2 = "%.2x" % (out2[k])
        else:
            v2 = "??"
        if verbose:
            print "%s\t%.2x\t%s" % (k, out1[k], v2)

    return res

for i in range(1000):
    dword1 = random.randint(0, 0xffffffff)
    dword2 = random.randint(0, 0xffffffff)
    out1 = run1(dword1, dword2)
    out2 = run2(dword1, dword2)
    res = diff(out1, out2, False)
    print "%.8x %.8x --> %s" % (dword1, dword2, res)
    assert res
