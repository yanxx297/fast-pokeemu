#!/bin/bash
test_qemu=false
clean=false
qemu_dir=.
revert=false
cc="ccache"
while [ "$1" != "" ]; do
	case $1 in
		--cache )
			shift
			cc=$1
			;;
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
        git clean -xdff -e bisect.sh -e check-qemu.sh -e ui/keycodemapdb/
        if ! [ -e ui/keycodemapdb/ ] && grep -q keycodemapdb .gitmodules; then
                git clone https://github.com/qemu/keycodemapdb.git ui/keycodemapdb
        fi
        seccomp=""
        if grep -q disable-seccomp configure; then
                seccomp="--disable-seccomp"
        fi
        capstone=""
        if grep -q disable-capstone configure; then
                seccomp="--disable-capstone"
        fi
        ./configure --disable-linux-user --target-list=i386-softmmu --enable-kemufuzzer --disable-kvm --disable-werror --cc=$cc" cc" --disable-fdt $seccomp $capstone
        make
        rv=$?
        # Terminate bisecting if compilation fails.
        if [ $rv -ne 0 ]; then
                make distclean
                if [ $rv -gt 127 ]; then
                        if [[ "$revert" == true ]]; then
                                exit 0
                        else
                                exit 127
                        fi
                else
                        if [[ "$revert" == true ]]; then
                                exit 0
                        else
                                exit $rv
                        fi
                fi
        fi
        if [[ "$test_qemu" == true ]];then
                chmod +x run-testcase
                timeout 10 ./run-testcase /tmp/floppy-dbg /tmp/out/dbg.post /tmp/out
                rv=$?
                if [ $rv -eq 0 ]; then
                        timeout 10 ../kvm-run/run-testcase /tmp/out/dbg.post.pre /tmp/out/00000000-kvm.post
                        python ../../scripts/diff_cpustate.py /tmp/out/dbg.post.post /tmp/out/00000000-kvm.post
                        rv=$?
                fi
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
