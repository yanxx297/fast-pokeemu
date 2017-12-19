#!/bin/bash
if [ -e kemufuzzer.c ]; then        
        seccomp=""
        if grep -q disable-seccomp configure; then
                seccomp="--disable-seccomp"
        fi
        ./configure --disable-linux-user --target-list=i386-softmmu --enable-kemufuzzer --disable-kvm --disable-werror --cc="ccache cc" $seccomp
        make
        rv=$?
        if [ $rv -gt 127 ]; then
                exit 127
        elif [ $rv -ne 0 ]; then
                exit $rv
        fi
        chmod +x run-testcase
        ./run-testcase /tmp/floppy-dbg /tmp/out/dbg.post /tmp/out
        ../../emulators/kvm-run/run-testcase /tmp/out/dbg.post.pre /tmp/out/00000000-kvm.post
        python ../../scripts/diff_cpustate.py /tmp/out/dbg.post.post /tmp/out/00000000-kvm.post
        rv=$?
        if [ $rv -gt 127 ]; then
                make distclean                
                exit 127
        else
                make distclean
                exit $rv
        fi
else
        echo "Ignore this branch"
fi
