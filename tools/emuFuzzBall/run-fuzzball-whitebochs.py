#!/usr/bin/env python
#useage: python run-fuzzball-whitebochs <whitebochs' dir>
import sys, os, subprocess, time, glob
from common import *

this = os.path.abspath(__file__)
root = os.path.abspath(os.path.join(os.path.dirname(this), ".."))
run_fuzzball = os.path.join(root, "FuzzBall/run-emu-fuzzball.py")
print run_fuzzball
fuzzball = os.path.join(root, "FuzzBall/emu_fuzzball")
print fuzzball
whitebochs = os.path.join(root, "WhiteBochs/fuzzball-whitebochs")
print whitebochs
snapshot = os.path.join(root, "Snapshots/base.snap")


def log(where, what):
    where = open(where, "w")
    where.write(what)
    where.close()


def md5file(what):
    what = open(what)
    h = md5(what)
    what.close()
    return h


args = []
for arg in sys.argv[1:]:
    args += glob.glob(arg)

for shellcode in args:
    t0 = time.time()

    if not os.path.isdir(shellcode):
        print shellcode
        print "not a path\n"
        continue

    sh = os.path.join(os.path.abspath(shellcode), "shellcode")
    print sh
    if os.path.isfile(sh) and mtime(sh) > max(mtime(fuzzball),
                                              mtime(run_fuzzball), 
                                              mtime(whitebochs), 
                                              mtime(snapshot),
                                              mtime(this)):
        continue

    here = lambda x: os.path.join(os.path.abspath(shellcode), x)

    env = os.environ.copy()
    env_ = {}
    env_["FUZZBALL_OUTDIR"] = os.path.abspath(shellcode)
    env_["FUZZBALL_MAX_ITERATIONS"] = os.getenv("MAX_ITERATIONS", "256")
 
    cmdline = [run_fuzzball, whitebochs, snapshot, to_c_str(shellcode)]
    for k, v in env_.iteritems():
        env[k] = v
        print "for_loop: %s=\"%s\"\n" % (k, v),
    print "Exit for_loop\n"
    print " ".join(cmdline)
    
    print cmdline
    subprocess.check_call(cmdline, env = env)
    

    print
    print 
    print
    print
