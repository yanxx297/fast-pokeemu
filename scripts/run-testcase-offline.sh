#! /bin/bash

aggreg=false
kvm=false
mode=
in_dir=
out_dir=
timeout=10
loop=1
tmp_dir=/tmp
emu_path=../emu/qemu/run-testcase

while [ "$1" != "" ]; do
	case $1 in
                -e | --emu )
                        shift
                        emu_path=$1
                        ;;
		-aggreg )
			aggreg=true
			;;
		-kvm )
			kvm=true
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
		-l | --loop )
			shift
			loop=$1
			;;
		-h | --help )
			echo "Usage: ./run-testcase.sh [-a] [-m 0~3] 
			 [-in path_to_FuzzBALL_test_inputs]"
			;;
	esac 
	shift
done

if ! [ -e $in_dir ] && [ "$kvm" == false ] ; then
	echo "Input folder $in_dir doesn't exist."
	exit
fi

if ! [ $out_dir ] ;then
	echo "Output folder $out_dir doesn't exist"
	exit
fi

mkdir -p $out_dir $tmp_dir
if ! [ -z $mode ]; then export MODE=$mode; fi
if ! [ -z $in_dir ]; then export IN=$in_dir; fi
if ! [ -z $out_dir ]; then export OUT=$out_dir; fi
if ! [ -z $tmp_dir ]; then export TMP_DIR=$tmp_dir; fi
if ! [ -z $timeout ]; then export TIMEOUT=$timeout; fi
if ! [ -z $loop ]; then export LOOP=$loop; fi
if ! [ -z $emu_path ] && [ "$kvm" == false ]; then export EMUPATH=$emu_path; fi

if [[ "$aggreg" == true ]]; then
	make -f batchRunAggregTC -i -j 6
	rm -r $tmp_dir/tmp.*
elif [[ "$kvm" == true ]]; then
	if [[ -z "$in_dir" ]]; then
		echo "Please set remote input directory with -in option"
	else
		insn_list=$(ls $in_dir)
		insn_list=$(echo $insn_list| tr "\n" " ")
		export INSN_LIST=$insn_list
		make -f batchRunTestcase-kvm-offline -i -j 6 all
	fi
else
	make -f batchRunTestcase -i -j 6
fi

rm -r /tmp/tmp.*
