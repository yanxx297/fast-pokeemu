#! /bin/bash

out=/home/yanxx297/Project/pokemu-oras/data/20171124
start=10

no_diff () {
        if ! [ -f $out/$2/mismatch ]; then
                return 0;
        elif ! grep -q $1 $out/$2/mismatch; then
                return 0;
        else
                return 1;
        fi
}

while [ "$1" != "" ]; do
        case $1 in
                -s )
                        shift
                        start=$1
                        ;;
                -h | --help )
                        echo "Usage: ./historical-bug.sh [-s START_NUMBER]
                        0       full experiment (start from aggreg-1 and aggreg-10000
                        1       run single tests of valid instructions"
                        ;;
        esac
        shift
done

if (( $start >= 10 )); then
        exit 0
fi

# pre-run aggreg tests
# Only pick aggreg tests that can find new diffs when loop increase from 1 to 10000
if (( $start <= 0 )); then 
        ./run-testcase-offline.sh -aggreg -m 3 -in $out/aggreg_list/ -out /tmp/out/aggreg-1/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in /home/yanxx297/Project/pokemu-oras/data/state-explr/ -out /tmp/out/aggreg-1/;
        ./run-testcase-offline.sh -aggreg -m 3 -l 10000 -in $out/aggreg_list/ -out /tmp/out/aggreg-10000/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in /home/yanxx297/Project/pokemu-oras/data/state-explr/ -out /tmp/out/aggreg-10000/
        mv /tmp/out/aggreg-1/ $out/
        mv /tmp/out/aggreg-10000/ $out/
        for line in $(cat $out/out/000); do 
                if [ -f $out/aggreg-10000/$line/mismatch ]; 
                then 
                        echo $line >> $out/historical-bug; 
                        mkdir $out/qemu-bug/
                        cp -r /home/yanxx297/Project/pokemu-oras/data/state-explr/$line $out/qemu-bug/;
                fi; 
        done
else
        echo "Skip aggreg-1 and aggreg-10000"
fi

# Run single tests
if (( $start <= 1 )); then
        echo "run single tests of valid instructions"
        ./run-testcase-offline.sh -m 3 -in $out/qemu-bug/ -out /tmp/out/single-1/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/qemu-bug/ -out /tmp/out/single-1/;
        ./run-testcase-offline.sh -m 3 -l 10000 -in $out/qemu-bug/ -out /tmp/out/single-10000/ -e ../emu/qemu/run-testcase;
        ./run-testcase-offline.sh -kvm -in $out/qemu-bug/ -out /tmp/out/single-10000/;
        echo "Switch to latest QEMU, recompile and rerun the single-10000 experiment"
        echo "  ./run-testcase-offline.sh -m 3 -l 10000 -in /home/yanxx297/Project/pokemu-oras/data/20171124/qemu-bug/ -out /tmp/out/single-10000-new/ -e ../emu/qemu/run-testcase"
        echo "  ./run-testcase-offline.sh -kvm -in /home/yanxx297/Project/pokemu-oras/data/20171124/qemu-bug/ -out /tmp/out/single-10000-new/"
        exit 0
else
        echo "Skip single tests"
fi

if (( $start <= 2 )); then
        for dir in $out/single-10000/*; do                 
                for file in $dir/*.diff; do                        
                        if [ -f $dir/mismatch ] && grep -q $(basename $file .diff) $dir/mismatch; then
#                                        echo $file >> $out/hisbug-candidate
                                        if $(no_diff $(basename $file .diff) single-10000-new/$(basename $dir)); then
                                                echo $file
#                                                echo $file >> $out/bisearch-list                                                
#                                                cat $file
                                        fi
                        fi
                done
        done
fi
