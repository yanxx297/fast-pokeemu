#Usage: ./analyze_shell_code.sh <testcase_dir>
TE=$(pwd)/..
$TE/scripts/gen_shell_code.py $(find $1 -name testcase) 
