#! /bin/bash

aggreg=false
mode=0
in_dir=/export/scratch/tmp/sample
out_dir=/export/scratch/tmp/out/
timeout=10
tmp_dir=/export/scratch/tmp

while [ "$1" != "" ]; do
	case $1 in
		-a | --aggreg )
			aggreg=true
			shift
			;;
		-m | --mode )
			shift
			mode=$1
			;;
		-in )
			shift
			in_dir=$1
			;;
		-out )
			shift
			out_dir=$1
			;;		
		-t | --timeout )
			shift
			timeout=$1
			;;
		-h | --help )
			echo "Usage: ./run-testcase.sh [-a] [-m 0~3] 
			 [-in path_to_FuzzBALL_test_inputs]"
			;;
	esac 
	shift
done

if ! [ -e $in_dir ]; then
	echo "Input folder doesn't exist."
	exit
fi
mkdir -p $out_dir $tmp_dir
export MODE=$mode
export IN=$in_dir
export OUT=$out_dir
export TMP_DIR=$tmp_dir
export TIMEOUT=$timeout

if [[ "$aggreg" == false ]]; then
	make -f batchRunTestcase -i -j 6
else
	make -f batchRunAggregTC -i -j 6
	rm -r $tmp_dir/tmp.*
fi

rm -r /tmp/tmp.*
