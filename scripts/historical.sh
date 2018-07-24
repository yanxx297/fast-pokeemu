#! /bin/bash

in=../data/state-explr
out=/tmp
single=false
aggreg=false
clean=false
iter=1
mode=0

# Run full experiment by default
start=0
stop=4

while [ "$1" != "" ]; do
        case $1 in
		-in )
			shift
			in=$1
			;;
		-m | --mode )
			shift
			mode=$1
			;;
		-i | --iter )
			shift
			iter=$1
			;;
                -c | --clean)
                        clean=true
                        ;;
                -a | --aggreg )
                        aggreg=true
                        ;;
                -n )
                        # Single step
                        single=true
                        ;;
                -from )
                        shift
                        start=$1
			;;
		-to )
			shift
			stop=$1
			;;
                -h | --help )
                        echo "Usage: ./historical.sh [-acn] [-s START_NUMBER]
                        0       Full experiment (run aggregations on both qemu-1.0 and most recent version)
                        1       Generate the insn list to run single tests
                        2       Rerun single tests for selected instructions (or all instuctions without -a
                        3       Collect single tests that are eligible for binary search
                        4       Binary search"
                        ;;
        esac
        shift
done

if ! [ -d $out/aggreg_list ]; then
        echo "Please copy all the aggregation list files to $out/aggreg_list"
        exit 0
fi

mkdir -p /tmp/out

if (( $start <= 0 )) && [ "$aggreg" == true ]; then
        echo "Run aggregation-$iter on both qemu-1.0 and most recent version"
        git -C ../emu/qemu checkout master
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -aggreg -m $mode -l $iter -in $out/aggreg_list/ -out $out/aggreg-$iter-new/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $in -out $out/aggreg-$iter-new/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout $(git -C ../emu/qemu rev-list HEAD | tail -n 1)
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -aggreg -m $mode -l $iter -in $out/aggreg_list/ -out $out/aggreg-$iter-old/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $in -out $out/aggreg-$iter-old/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout master
        if [ "$clean" == true ]; then
                clean_dir $out/aggreg-$iter-new/
                clean_dir $out/aggreg-$iter-old/
        fi
        if [ "$single" == true ]; then
                exit 0
        fi
fi
if (( $stop <= 0 )); then
	exit 0
fi

if (( $start <= 1 )) && (( $stop >= 1 )) && [ "$aggreg" == true ]; then
        echo "Generate the insn list to run single tests"
        mkdir $out/state-explr-$iter
        for line in $out/aggreg-$iter-old/*; do
                if [ -f $line/mismatch ] && ! [ -f $out/aggreg-$iter-new/$(basename $line)/mismatch ]; then
                        echo $(basename $line) >> $out/rerun_list_$iter
                        cp -r $in/$(basename $line) $out/state-explr-$iter
                fi
        done
        if [ "$single" == true ]; then
                exit 0
        fi
elif (( $start <= 1 )) && (( $stop >= 1 )); then
        echo "insn list for single tests = all instructions"
        mkdir $out/state-explr-$iter
        for line in $in/*; do
                mkdir $out/state-explr-$iter/$(basename $line)
                cp $line/* $out/state-explr-$iter/$(basename $line)/
                for file in $line/*; do
                        if grep -q $(basename $file) $out/aggreg_list/$(basename $line)/*; then 
                                cp -r $file $out/state-explr-$iter/$(basename $line)/
                        fi
                done
        done
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 2 )) && (( $stop >= 2 )); then
        if [ "$aggreg" == true ]; then
                echo "Rerun single tests"
        else
                echo "Run all valid single tests"
        fi
        git -C ../emu/qemu checkout master
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -m $mode -l $iter -in $out/state-explr-$iter -out $out/single-$iter-new/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/state-explr-$iter -out $out/single-$iter-new/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout $(git -C ../emu/qemu rev-list HEAD | tail -n 1)
        cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; cd -
        ./run-testcase-offline.sh -m $mode -l $iter -in $out/state-explr-$iter -out $out/single-$iter-old/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/state-explr-$iter -out $out/single-$iter-old/;
        cd ../emu/qemu && make distclean; cd -
        git -C ../emu/qemu checkout .
        git -C ../emu/qemu checkout master
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 3 )) && (( $stop >= 3 )); then
        mkdir $out/diffs_$iter/
        for dir in $out/single-$iter-old/*; do
                echo $dir
                for file in $dir/*.diff; do
                        if [ -f $out/single-$iter-old/$(basename $dir)/mismatch ] && grep -q $(basename $file .diff) $out/single-$iter-old/$(basename $dir)/mismatch\
                                && [ -f $out/single-$iter-new/$(basename $dir)/match ] && grep -q $(basename $file .diff) $out/single-$iter-new/$(basename $dir)/match; then
                                echo $(basename $file .diff) >> $out/diffs_$iter/$(basename $dir)
                        fi
                done
        done
        if [ "$single" == true ]; then
                exit 0
        fi
fi

if (( $start <= 4 )) && (( $stop >= 4 )); then
        mkdir -p $out/bisect_$iter
        for file in $out/diffs_$iter/*; do
                cd ../emu/qemu && ./check-qemu.sh; chmod +x run-testcase; chmod +x run-testcase-debug; cd -
                python run_test_case.py testcase:$in/$(basename $file)/$(sort -R $file| head -n 1)/testcase\
                        timeout:10 outdir:/tmp/out script:../emu/qemu/run-testcase-debug mode:$mode loop:$iter
                cd ../emu/qemu
                make distclean
                git checkout .
                ./bisect.sh $out/bisect_$iter/$(basename $file).log
                cd -
        done
        if [ "$single" == true ]; then
                exit 0
        fi
fi
