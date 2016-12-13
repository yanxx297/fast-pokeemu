#!/bin/bash
# Usage: ./wrapper_diff_cpustate.sh <qemu .post memdump folder> <kvm .post memdump folder> <output folder>
# Comparing each .post with the same name in 2 folders using diff_cpustate.py.   

QDIR=$1
KDIR=$2
OUT=$3


for dir in $QDIR/*;
do
	CODE=$(basename $dir);
	echo $CODE;
	OUTDIR=$OUT/$CODE;
	mkdir $OUTDIR;
	for file in $dir/*.post;
	do
		ID=$(basename $file);
		python diff_cpustate.py $QDIR/$CODE/$ID $KDIR/$CODE/$ID > $OUTDIR/$ID.diff;
	done	
done;
	

