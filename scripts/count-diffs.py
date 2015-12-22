import sys, re

normalize = ["cpu[0].sregs_state.ldt.type", "cpu[0].sregs_state.ldt.present",
             "cpu[0].sregs_state.ldt.l", "cpu[0].regs_state.rflags", 
             "cpu[0].sregs_state.ds.s", "cpu[0].sregs_state.ss.s", 
             "cpu[0].sregs_state.es.s", "cpu[0].sregs_state.fs.s", 
             "cpu[0].sregs_state.gs.s", "cpu[0].sregs_state.tr.l",
             "cpu[0].sregs_state.gs.selector", 
             "cpu[0].sregs_state.ss.selector", 
             "cpu[0].sregs_state.ds.selector", 
             "cpu[0].sregs_state.es.selector", 
             "cpu[0].sregs_state.fs.selector", 
             ]
normalize = []

nondet = ["3e0f31", "0f01c1", "660f7d00", "642ecc", "0f624500", "260f6100", "3e0f33", "642ecc", "3e0fa2"]

def isnondet(x):
    x = x.split("/")
    return x[1] in nondet

diffs_bochs = {}
diffs_qemu = {}
for l in sys.stdin.readlines():
    l = l.strip("\n")

    if l.startswith("cpu[0].regs_state.rip"): 
        continue

    if l.startswith("./"):
        if len(diffs_bochs) > 1: 
            if not isnondet(diffs_bochs["testcase"]):
                print "BOCHS", diffs_bochs
        if len(diffs_qemu) > 1:
            if not isnondet(diffs_qemu["testcase"]):
                print "QEMU", diffs_qemu
        diffs_qemu = {}
        diffs_bochs = {}

        diffs_qemu["testcase"] = l
        diffs_bochs["testcase"] = l



    if l.startswith("cpu[0]") or l.startswith("mem"):
        ll = l.split()
        t, qemu, bochs, kvm = ll[0], int(ll[1],16), int(ll[2], 16), int(ll[3], 16)
        if normalize and t in normalize:
            continue

        if t == "cpu[0].exception_state.vector":
            if kvm == 7:
                continue
            if bochs == qemu == 6:
                continue

        if kvm != bochs and t != "cpu[0].regs_state.rsp" and \
                not (t == "cpu[0].exception_state.vector" and qemu == 13 \
                         and kvm == 65535):
            diffs_bochs[t] = (bochs, kvm)
        if kvm != qemu:
            diffs_qemu[t] = (qemu, kvm)

