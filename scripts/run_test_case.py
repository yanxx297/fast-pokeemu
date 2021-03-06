#!/usr/bin/env python

import os, subprocess, signal, time
from gen_floppy_image import gen_floppy_with_testcase
from common import *
from cpustate_x86 import *

autodelete = True

class Timeout(Exception):
    pass

def exec_with_timeout(cmdline, timeout = None):
    # Execute setpgid before exec to make all the children killable
    child = subprocess.Popen(cmdline, stdin = NULL, stderr = subprocess.STDOUT,
                             preexec_fn = lambda: os.setpgid(0, 0))

    if not timeout:
        ret = child.wait()
    else:
        wait_till = time.time() + timeout

        while child.poll() == None and time.time() < wait_till:
            time.sleep(0.1)

        if time.time() >= wait_till:
            # Kill the child and its children as well
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except OSError:
                pass
            raise Timeout

        ret = child.returncode
    
    if ret != 0:
        raise OSError

    child.communicate()

    return ret


def create_dummy_state(f, typ, emu, kernel_version, kernel_md5, testcase_md5):
    hdr = header_t()
    hdr.magic      = CPU_STATE_MAGIC
    hdr.version    = CPU_STATE_VERSION
    hdr.type       = typ
    hdr.cpusno     = 0
    hdr.mem_size   = 0
    hdr.emulator   = emu
    hdr.kernel_version = kernel_version
    hdr.kernel_checksum = kernel_md5
    hdr.testcase_checksum = testcase_md5

    s = string_at(byref(hdr), sizeof(hdr))
    f = gzip.open(f, 'w')
    f.write(s)
    f.close()


# build a temporary floppy image with the test-case
def gen_floppy(testcase, mode, loop):
    floppy = Tempfile(delete = autodelete)
    gen_floppy_with_testcase(testcase = testcase, floppy = floppy, mode = mode, loop = loop)
    return floppy


# extract testcase name from filename (assume the following directory
# structure: code/pathno/testcase)
def gen_testcase_name(testcase):
    assert os.path.basename(testcase) == "testcase"
    testcase = os.path.dirname(os.path.abspath(testcase)).split("/")
    assert len(testcase) >= 2
    code, path = testcase[-2], testcase[-1]
    return code, path


# run a given testcase and the result somewhere (assume the script for running
# the emulator accepts the floppy image as first argument and an output prefix
# as second argument)
def run_testcase(outdir, code, path, script, floppy, timeout, tmp):
    mkdir(outdir)
    outprefix = os.path.join(outdir, path)
    cmdline = [script, str(floppy), outprefix, tmp]
    print cmdline
    
    try:
        t0 = time.time()
        exec_with_timeout(cmdline = cmdline, timeout = timeout)
        exectime = time.time() - t0
        print "done in %.3fs" % (exectime)
    except Timeout:
        # We no longer create a fake poststate here, and the prestate
        # may not exist either.
        print "TIMEOUT!!!!"
        exit(0)


if __name__ == "__main__":
    opts = {"testcase" : None, "outdir" : None, "script" : None, "timeout" : 10, "mode": 0, \
            "tmp": "", "loop": 1}

    for arg in sys.argv[1:]:
        a = arg.split(":")
        assert len(a) == 2
        k, v = a
        if k in opts:
            opts[k] = v
        else:
            assert 0

    for v in opts.itervalues():
        assert v is not None

    #TODO: check that each testcase is a file
    #assert os.path.isfile(opts["testcase"])
    assert os.path.isdir(opts["outdir"])
    print "outdir valid\n"
    assert os.path.isfile(opts["script"]), opts["script"]

    floppy = gen_floppy(opts["testcase"], opts["mode"], opts["loop"])
    code, path = gen_testcase_name(opts["testcase"])
    run_testcase(opts["outdir"], code, path, opts["script"], floppy, 
                 int(opts["timeout"]), opts["tmp"])
