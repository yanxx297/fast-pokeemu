#! /bin/bash
out=/tmp/out
start=10

while [ "$1" != "" ]; do
        case $1 in
                -out )
                        shift
                        out=$1
                        ;;
                -s )
                        shift
                        start=$1
                        ;;
                -h | --help )
                        echo "Usage: ./historical-bug-vanilla.sh [-s START_NUMBER] [-out OUTDIR]
                        0       full experiment (single-m0 on QEMU 1.0 
                        1       single-m0 on QEMU 2.4
                        2       collect diffs"
                        ;;
        esac
        shift
done

if (( $start >= 10 )); then
        exit 0
fi

if (( $start <= 2 )); then
        mkdir $out/diffs/
        for dir in $out/single-m0-10/*; do
                echo $dir
                for file in $dir/*.diff; do
                        if [ -f $out/single-m0-10/$(basename $dir)/mismatch ] && grep -q $(basename $file .diff) $out/single-m0-10/$(basename $dir)/mismatch\
                                && [ -f $out/single-m0-24/$(basename $dir)/match ] && grep -q $(basename $file .diff) $out/single-m0-24/$(basename $dir)/match; then
                                echo $(basename $file .diff) >> $out/diffs/$(basename $dir)
                        fi
                done
        done
fi

if (( $start <= 3 )); then
        mkdir -p $out/bisect
        for file in $out/diffs/*; do
                python run_test_case.py testcase:/home/yanxx297/Project/pokemu-oras/data/state-explr/$(basename $file)/$(sort -R $file| head -n 1)/testcase\
                        timeout:10 outdir:/tmp/out script:/home/yanxx297/Project/pokemu-oras/emu/qemu-0.12.4/run-testcase-debug mode:0
                cd ../emu/qemu
                ./bisect.sh $out/bisect/$(basename $file).log
                cd -
        done
fi
