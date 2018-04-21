#!/bin/bash
test_qemu=false
clean=false
qemu_dir=.
revert=false
while [ "$1" != "" ]; do
	case $1 in
                -r | --revert )
                        revert=true
                        ;;
                -c | --clean )
                        clean=true
                        ;;
                -t | --test-qemu )
                        test_qemu=true
                        ;;                        
		-h | --help )
			echo "Usage: ./check-qemu.sh [-ct]
                        -t      Test correctness
                        -c      clean compilation"
                        exit
			;;
	esac 
	shift
done
if [ -e kemufuzzer.c ]; then        
        seccomp=""
        if grep -q disable-seccomp configure; then
                seccomp="--disable-seccomp"
        fi
        ./configure --disable-linux-user --target-list=i386-softmmu --enable-kemufuzzer --disable-kvm --disable-werror --cc="ccache cc" $seccomp
        make
        rv=$?
        # Quit eariler if compilation fails.
        if [ $rv -gt 127 ]; then
                if [[ "$revert" == true ]]; then
                        exit 0
                else
                        exit 127
                fi
        elif [ $rv -ne 0 ]; then
                if [[ "$revert" == true ]]; then
                        exit 0
                else
                        exit $rv
                fi
        fi
        if [[ "$test_qemu" == true ]];then
                chmod +x run-testcase
                ./run-testcase /tmp/floppy-dbg /tmp/out/dbg.post /tmp/out
                ../kvm-run/run-testcase /tmp/out/dbg.post.pre /tmp/out/00000000-kvm.post
                python ../../scripts/diff_cpustate.py /tmp/out/dbg.post.post /tmp/out/00000000-kvm.post
                rv=$?
        fi
        if [ $rv -gt 127 ]; then
                if [[ "$clean" == true ]]; then
                        make distclean
                fi
                if [[ "$revert" == true ]]; then
                        exit 0
                else
                        exit 127
                fi
        else
                if [[ "$clean" == true ]]; then
                        make distclean
                fi
                if [[ "$revert" == true ]]; then
                        if [ $rv -eq 0 ]; then
                                exit 1
                        else
                                exit 0
                        fi
                else
                        exit $rv
                fi
        fi
else
        echo "Ignore this branch"
fi
