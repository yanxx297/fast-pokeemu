#! /bin/bash
# Repeat the testing process of <testcase> for <time> times, including testcase generation.
# The results of comparison are redirected to <output>
# Usage: ./repeat-run-testcase.sh <time> <testcase> <output>

emu=../emu/qemu
kvm=../emu/kvm-run
count=$1

if ! [ -e $emu/i386-softmmu/qemu-system-i386 ]; then
        cd $emu; ./check-qemu.sh; chmod +x run-testcase; chmod +x run-testcase-debug; cd -
else
        echo "No need to recompile QEMU"
fi

mkdir -p /tmp/out
while [ $count -gt 0 ];do
        python run_test_case.py testcase:$2 timeout:10 outdir:/tmp/out script:$emu/run-testcase-debug mode:3 loop:10000
        cd $emu; ./run-testcase /tmp/floppy-dbg /tmp/out/dbg.post /tmp/out; rq=$?; cd -
        cd $kvm; timeout 10 ./run-testcase /tmp/out/dbg.post.pre /tmp/out/00000000-kvm.post; rk=$?; cd -
        if [ $rq == 0 ] && [ $rk == 0 ]; then
                python diff_cpustate.py /tmp/out/dbg.post.post /tmp/out/00000000-kvm.post |tee -a $3
        else
                echo "Timeout or something else goes wrong." >> $3
        fi
        echo "" >> $3
        let count=count-1
done
