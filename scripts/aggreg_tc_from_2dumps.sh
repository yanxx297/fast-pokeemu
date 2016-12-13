#!/bin/bash
#Usage: ./aggreg_tc_from_dump.sh <path/to/testcase/dir/> <path/to/memdump/dir1/> <path/to/memdump/dir2/>
TC=""
SCRIPT=$(pwd)
TCDIR=$1
QDUMPDIR=$2
KDUMPDIR=$3
cd $TCDIR
for dir in */ ;
do
	QDUMP=$QDUMPDIR${dir::-1}".post"
	KDUMP=$KDUMPDIR${dir::-1}".post" 
	TCPATH=$TCDIR$dir"testcase"
	QEXIT=$(python $SCRIPT/diff_cpustate.py $QDUMP| grep 'No Exception'| wc -l)
	KEXIT=$(python $SCRIPT/diff_cpustate.py $KDUMP| grep 'No Exception'| wc -l)
	if [[ $QEXIT != "0" ]] && [[ $KEXIT != "0" ]]; then
		if [[ $TC == "" ]]; then
			TC=$TCPATH
		else		
			TC=$TC","$TCPATH
		fi
	fi	
	
done
echo $TC

