#! /bin/bash

in=../data/state-explr
out=/tmp
single=false
aggreg=false
clean=false

while [ "$1" != "" ]; do
        case $1 in
                -c | --clean)
                        clean=true
                        ;;
                -a | --aggreg )
                        aggreg=true
                        ;;
                -n )
                        single=true
                        ;;
                -s )
                        shift
                        start=$1
                        ;;
                -h | --help )
                        echo "Usage: ./historical-bug.sh [-acn] [-s START_NUMBER]
                        0       Full experiment (run aggreg-1 and aggreg-10000 on both qemu-1.0 and most recent version)
                        1       Generate the insn list to run single tests
                        2       Rerun single tests for selected instructions (or all instuctions without -a
                        3       Collect single tests that are eligible for binary search
                        4       Binary search"
                        ;;
        esac
        shift
done

if (( $start >= 10 )); then
        exit 0
fi

mkdir -p /tmp/out
if (( $start <= 0 )) && [ "$aggreg" == true ]; then
        echo "Run aggreg-1 and aggreg-10000 on both qemu-1.0 and most recent version"
        git -C ../emu/qemu checkout master
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -aggreg -m 3 -in $out/aggreg_list/ -out $out/aggreg-1-new/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $in -out $out/aggreg-1-new/;
        ./run-testcase-offline.sh -aggreg -m 3 -l 10000 -in $out/aggreg_list/ -out $out/aggreg-10000-new/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $in -out $out/aggreg-10000-new/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout $(git -C ../emu/qemu rev-list HEAD | tail -n 1)
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -aggreg -m 3 -in $out/aggreg_list/ -out $out/aggreg-1-old/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $in -out $out/aggreg-1-old/;
        ./run-testcase-offline.sh -aggreg -m 3 -l 10000 -in $out/aggreg_list/ -out $out/aggreg-10000-old/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $in -out $out/aggreg-10000-old/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout master
        if [ "$clean" == true ]; then
                clean_dir $out/aggreg-10000-new/
                clean_dir $out/aggreg-10000-old/
                clean_dir $out/aggreg-1-new/
                clean_dir $out/aggreg-1-old/
        fi
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 1 )) && [ "$aggreg" == true ]; then
        echo "Generate the insn list to run single tests"
        mkdir $out/state-explr-1
        mkdir $out/state-explr-10000
        for line in $out/aggreg-1-old/*; do
                if [ -f $line/mismatch ] && ! [ -f $out/aggreg-1-new/$(basename $line)/mismatch ]; then
                        echo $(basename $line) >> $out/rerun_list_1
                        cp -r $in/$(basename $line) $out/state-explr-1
                fi
        done
        for line in $out/aggreg-10000-old/*; do
                if [ -f $line/mismatch ] && ! [ -f $out/aggreg-10000-new/$(basename $line)/mismatch ]; then
                        echo $(basename $line) >> $out/rerun_list_10000
                        cp -r $in/$(basename $line) $out/state-explr-10000
                fi
        done
        if [ "$single" == true ]; then
                exit 0
        fi
elif (( $start <= 1 )); then
        echo "insn list for single tests = all instructions"
        mkdir $out/state-explr
        for line in $in/*; do
                mkdir $out/state-explr/$(basename $line)
                cp $line/* $out/state-explr/$(basename $line)/
                for file in $line/*; do
                        if grep -q $(basename $file) $out/aggreg_list/$(basename $line)/*; then 
                                cp -r $file $out/state-explr/$(basename $line)/
                        fi
                done
        done
        ln -s $out/state-explr $out/state-explr-1
        ln -s $out/state-explr $out/state-explr-10000
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 2 )); then
        if [ "$aggreg" == true ]; then
                echo "Rerun single tests"
        else
                echo "Run all valid single tests"
        fi
        git -C ../emu/qemu checkout master
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -m 0 -in $out/state-explr-1 -out $out/single-1-new/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/state-explr-1 -out $out/single-1-new/;
        ./run-testcase-offline.sh -m 3 -l 10000 -in $out/state-explr-10000 -out $out/single-10000-new/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/state-explr-10000 -out $out/single-10000-new/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout $(git -C ../emu/qemu rev-list HEAD | tail -n 1)
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -m 0 -in $out/state-explr-1 -out $out/single-1-old/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/state-explr-1 -out $out/single-1-old/;
        ./run-testcase-offline.sh -m 3 -l 10000 -in $out/state-explr-10000 -out $out/single-10000-old/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/state-explr-10000 -out $out/single-10000-old/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout master
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 3 )); then
        mkdir $out/diffs_1/
        mkdir $out/diffs_10000/
        for dir in $out/single-1-old/*; do
                echo $dir
                for file in $dir/*.diff; do
                        if [ -f $out/single-1-old/$(basename $dir)/mismatch ] && grep -q $(basename $file .diff) $out/single-1-old/$(basename $dir)/mismatch\
                                && [ -f $out/single-1-new/$(basename $dir)/match ] && grep -q $(basename $file .diff) $out/single-1-new/$(basename $dir)/match; then
                                echo $(basename $file .diff) >> $out/diffs_1/$(basename $dir)
                        fi
                done
        done
        for dir in $out/single-10000-old/*; do
                echo $dir
                for file in $dir/*.diff; do
                        if [ -f $out/single-10000-old/$(basename $dir)/mismatch ] && grep -q $(basename $file .diff) $out/single-10000-old/$(basename $dir)/mismatch\
                                && [ -f $out/single-10000-new/$(basename $dir)/match ] && grep -q $(basename $file .diff) $out/single-10000-new/$(basename $dir)/match; then
                                echo $(basename $file .diff) >> $out/diffs_10000/$(basename $dir)
                        fi
                done
        done
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 4 )); then
        mkdir -p $out/bisect_1
        for file in $out/diffs_1/*; do
                cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; chmod +x run-testcase-debug; cd -
                python run_test_case.py testcase:$in/$(basename $file)/$(sort -R $file| head -n 1)/testcase\
                        timeout:10 outdir:/tmp/out script:/home/yanxx297/Project/pokemu-oras/emu/qemu/run-testcase-debug mode:0
                cd ../emu/qemu
                make distclean
                git checkout .
                ./bisect.sh $out/bisect_1/$(basename $file).log
                cd -
        done
        mkdir -p $out/bisect_10000
        for file in $out/diffs_10000/*; do
                cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; chmod +x run-testcase-debug; cd -
                python run_test_case.py testcase:$in/$(basename $file)/$(sort -R $file| head -n 1)/testcase\
                        timeout:10 outdir:/tmp/out script:/home/yanxx297/Project/pokemu-oras/emu/qemu/run-testcase-debug mode:3 loop:10000
                cd ../emu/qemu
                make distclean
                git checkout .
                ./bisect.sh $out/bisect_10000/$(basename $file).log
                cd -
        done
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 10 )); then
        if [ "$single" == true ]; then
                exit 0
        fi
fi
