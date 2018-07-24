#! /bin/bash
# Usage: ./repeat-hisbug.sh <time> <input>
# Repeat (part of) historical.sh for a fixed amount of <time> times

count=$1
loop=10000
mode=3

while [ $count -gt 0 ]; do
	let iter=$1-count
	./historical.sh -in $2 -i $loop -m $mode -to 3
	rm -rf /tmp/state-explr-$loop
	mkdir /tmp/out/round_$iter
	mv /tmp/single-$loop-new /tmp/out/round_$iter
	mv /tmp/single-$loop-old /tmp/out/round_$iter
	mv /tmp/diffs_$loop /tmp/out/round_$iter
	let count=count-1
done

# Check results.
# Uncomment the next line and run ./repeat-hisbug.sh 0 <input> if you only want to do the check.
#count=3
mkdir -p /tmp/out/
for file in /tmp/out/round_0/diffs_10000/*; do
	iter=2
	insn=$(basename $file)
	cmd="comm -12 /tmp/out/round_0/diffs_10000/$insn /tmp/out/round_1/diffs_10000/$insn"; 
	while [ $count -gt $iter ]; do 
		cmd+="|comm -12 - /tmp/out/round_$iter/diffs_10000/$insn";
		let iter=iter+1; 
	done; 
	echo $cmd
	eval $cmd > /tmp/out/$insn.log
done
