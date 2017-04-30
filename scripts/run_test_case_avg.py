#!/usr/bin/env python

from run_test_case import *

# Run one test case for once and return time  
def run_test_case(args):

    t0 = time.time()
    run_testcase(*args)
    t1 = time.time()
    print >> sys.stderr, "Done in %.3fs" % (t1 - t0)
    return  (t1 - t0)

# Execute function foo for n times, and get average result of foo
def get_avg(foo, opts, n):
    print "repeat by %d times" % n
    count = n
    s = 0;
    while count != 0:
        s += foo(opts)
        count -= 1
    return (s / n)


if __name__ == "__main__":
    opts = {"testcase" : None, "outdir" : None, "script" : None, "timeout" : 10, "mode": 0, "tmp":None}
    extraopts = {"repeat" : 1}

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

    for v in opts.itervalues():
        assert v is not None

    #TODO: check that each testcase is a file
    #assert os.path.isfile(opts["testcase"])
    assert os.path.isdir(opts["outdir"])
    print "outdir valid\n"
    assert os.path.isfile(opts["script"]), opts["script"]
    floppy = gen_floppy(opts["testcase"], opts["mode"])
    code, path = gen_testcase_name(opts["testcase"])    

    args = (opts["outdir"], code, path, opts["script"], floppy,int(opts["timeout"]), opts["tmp"])
    t = get_avg(run_test_case, args, int(extraopts["repeat"]))
    filename = opts["outdir"] + "/time"
    f = open(filename, 'a')
    f.write("%f\n" % t)
    f.close()
    print "avg time = %.3fs" % t
                 
    
