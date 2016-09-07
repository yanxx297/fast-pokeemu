#!/bin/bash
# Run a list of test cases according to a file 'insn'
# Usage: ./run-CPU-explr.sh path/to/output < /path/to/insn
while read -r code typ
do
	echo $code
	python run-emu-fuzzball.py ~/Project/pokemu-oras/tools/WhiteBochs-old/fuzzball-whitebochs ~/Project/pokemu-oras/base.snap $code
	mv $1 $1/../$typ		
done
