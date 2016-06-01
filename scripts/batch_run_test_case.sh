#!/bin/bash
#Usage: ./batch_run_test_case.sh <path/to/testcase/root> <emulator name> <aggregate or not: 1/0>
HOME=$(pwd);
TCPATH=$1;
TIMEOUT=5;
OUTDIR="/tmp/out/";
EMUPATH=$HOME/../emu/;
EMU=$EMUPATH$2"/run-testcase";

for dir in $TCPATH*/ ;
do
	dir=$dir"testcase" 
	echo $dir
	python run_test_case.py testcase:$dir timeout:$TIMEOUT outdir:$OUTDIR script:$EMU aggreg:$3
done
