#!/bin/bash
#Usage: ./batch_run_test_case.sh <path/to/testcase/root> <emulator name> <mode: 0/1/2/3>
DIR=$(pwd);
TCPATH=$1;
TIMEOUT=100;
OUTDIR="/export/scratch/tmp/out/";
EMUPATH=$DIR/../emu/;
EMU=$EMUPATH$2"/run-testcase";

for dir in $TCPATH*/ ;
do
	dir=$dir"testcase" 
	echo $dir
	echo python run_test_case.py testcase:$dir timeout:$TIMEOUT outdir:$OUTDIR script:$EMU mode:$3 
done
