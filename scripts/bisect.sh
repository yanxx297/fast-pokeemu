#! /bin/bash
python run_test_case.py testcase:/home/yanxx297/Project/pokemu-oras/data/state-explr/ARPL_EwGw/00000000/testcase timeout:10 outdir:/tmp/out script:/home/yanxx297/Project/pokemu-oras/emu/qemu-0.12.4/run-testcase-debug mode:2
../emu/qemu-0.12.4/run-testcase /tmp/floppy-dbg /tmp/out/dbg.post /tmp/out
../emu/kvm-run/run-testcase /tmp/out/dbg.post.pre /tmp/out/00000000-kvm.post
python diff_cpustate.py /tmp/out/dbg.post.post /tmp/out/00000000-kvm.post
rv=$?
if [ $rv -ne 0 ]; then
        exit 0
else
        exit 1
fi
