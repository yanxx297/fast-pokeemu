#!/bin/bash
#Usage: ./aggreg_tc_from_dump.sh <path/to/testcase/dir/> <path/to/memdump/dir/>
TC=""
SCRIPT=$(pwd)
TCDIR=$1
DUMPDIR=$2
cd $TCDIR
for dir in */ ;
do
#	echo ${dir::-1}
	DUMP=$DUMPDIR${dir::-1}".post"
	TCPATH=$TCDIR$dir"testcase"
#	echo $DUMP
	EXIT=$(python $SCRIPT/diff_cpustate.py $DUMP| grep 'No Exception'| wc -l)
	if [[ $EXIT != "0" ]]; then
		if [[ $TC == "" ]]; then
			TC=$TCPATH
		else		
			TC=$TC","$TCPATH
		fi
	fi	
	
done
echo $TC

