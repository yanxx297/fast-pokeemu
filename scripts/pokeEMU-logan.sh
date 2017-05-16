#! /bin/bash
dir=/export/scratch/tmp
in=$dir/aggreg_list/
out=$dir/out/

#./run-testcase.sh -aggreg -m 1 -in $in -out $out
#mv $out $dir/aggreg-m1-qemu/
#./run-testcase.sh -aggreg -m 2 -in $in -out $out
#mv $out $dir/aggreg-m2-qemu/

# for loop=10000 mode3
./run-testcase.sh -aggreg -m 3 -in $in -out $out
mv $out $dir/aggreg-m3-qemu-10000/

# output performance results
# TODO: finish it
for dir in /home/grad01/yan/tmp/single-m0-qemu/*; 
do 
	for dump in $dir/*.post; 
	do 
		for log in /home/grad01/yan/tmp/aggreg_list/$(basename $dir)/*.log; 
		do 
			if grep -q $(basename $dump .post) $log; then 
				cat $log >> count-m0; 
			fi; 
		done; 
	done; 
done;
for dir in /home/grad01/yan/tmp/single-m0-qemu/*; 
do 
	echo $dir; 
	cat $dir/time >> tmp-m0; 
done
