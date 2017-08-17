#! /bin/bash
dir=/export/scratch/tmp
in=$dir/aggreg_list/
out=$dir/out/

# output performance results
count_time () {
        for folder in $dir/aggreg-$1-qemu/*; 
        do 
                for dump in $folder/*.post; 
                do 
                        for log in $in/$(basename $folder)/*.log; 
                        do 
                                if grep -q $(basename $dump .post) $log; then 
                                        cat $log >> count-$1; 
                                fi; 
                        done; 
                done; 
        done;
        for folder in $dir/aggreg-$1-qemu/*; 
        do 
                echo $folder; 
                cat $folder/time >> time-$1; 
        done
}

#./run-testcase.sh -aggreg -m 1 -in $in -out $out
#mv $out $dir/aggreg-m1-qemu/
#count_time m1
#./run-testcase.sh -aggreg -m 2 -in $in -out $out
#mv $out $dir/aggreg-m2-qemu/
#count_time m2
#./run-testcase.sh -aggreg -m 3 -in $in -out $out
#mv $out $dir/aggreg-m3-qemu/
#count_time m3

# for loop=10000 mode3
#./run-testcase.sh -aggreg -m 3 -in $in -out $out
#mv $out $dir/aggreg-10000m3-qemu/
count_time 10000m3

