#Usage: ./analyze_shell_code.sh <testcase_dir>
TE=$HOME/Project/nsf-EmuVerify

tmp=$(mktemp)
cp $TE/tools/WhiteBochs-old/concrete-whitedisasm $tmp
chmod 700 $tmp

$TE/scripts/gen_shell_code.py $(find $1 -name testcase) 
#| while read shellcode; do $tmp "$shellcode"; done
rm -f $tmp
