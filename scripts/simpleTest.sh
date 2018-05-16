#! /bin/bash
default='\033[0m'
dim_color='\033[1;33m'
highlight='\033[1;31m'
out=/tmp
shellcode=
aggreg=
insn="simple-test"
emu_path=../emu/qemu/run-testcase
clean=true

while [ "$1" != "" ]; do
        case $1 in
		--disable-clean )
			clean=false
			;;
		-e | --emu )
			shift
			emu_path=$1
			;;
		--out )
			shift
			out=$1
			;;
		--aggreg-test )
			aggreg=true
			;;
		--single-test )
			aggreg=false
			;;
		-s | --shellcode )
			shift
			shellcode=$1
			;;
                -h | --help )
                        echo "Usage: ./simpleTest.sh [-s <shellcode>] [-e <path/to/emulator/run-testcase>]
	[--single-test] [--aggreg-test]"
			exit 0
                        ;;
        esac
        shift
done

if ! [ "$aggreg" == true ] && ! [ "$aggreg" == false ]; then
	echo "Neither --single-test nor --aggreg-test is set. 
	Please set one of them (but not both.)"
	exit 0
fi

mkdir -p $out/state-explr
mkdir -p $out/aggreg_list
mkdir -p /tmp/out
while IFS=$'\t' read -r -a line
do
	if [ $shellcode == ${line[0]} ]; then
		insn=${line[3]}
		break
	fi
done < ../data/instructions.csv

if [ -d ../data/state-explr/$insn ]; then
	echo "State files alreay exist for $insn, skip machine state exploring..."
	cp -r ../data/state-explr/$insn $out/state-explr/$insn
else
	echo "Machine states for $insn absent. Start regeneration..."
	cd ../tools/emuFuzzBall
	echo -e ${dim_color}
	python run-emu-fuzzball.py ../WhiteBochs-old/fuzzball-whitebochs ../../base.snap $shellcode $out/state-explr/$insn
	echo -e ${default}
	cd -
fi

if [ -d ../data/state-explr/$insn ] && ( [ -d ../data/aggreg_list/$insn ] || [ "$aggreg" == false ]); then
	echo "No need to regenerate aggregation list."
	cp -r ../data/aggreg_list/$insn $out/aggreg_list/
else
	echo "Prerun tests to regenerate aggregation list...(may take a while)"
	./run-testcase-offline.sh -m 3 -in $out/state-explr -out $out/single-m3/ -e $emu_path
	./run-testcase-offline.sh -kvm -in $out/state-explr -out $out/single-m3/
	mkdir $out/aggreg_list/$insn
	for file in $out/single-m3/*.diff; do
		echo $out/state-explr/$(basename $file .diff)/testcase >> $out/aggreg_list/$insn/log
	done
	var=$(tr "\n" "," < $out/aggreg_list/$insn/log)
	echo ${var::-1} > $out/aggreg_list/$insn/log
	python split_log.py $out/aggreg_list/$insn/log 600
	rm $out/aggreg_list/$insn/log 
fi

if [ "$aggreg" == true ]; then
	echo "Test the instruction in Fast PokeEMU mode"
	./run-testcase-offline.sh -aggreg -m 3 -in $out/aggreg_list/ -out $out/aggreg/ -e $emu_path
	./run-testcase-offline.sh -kvm -in $out/state-explr -out $out/aggreg/
elif [ "$aggreg" == false ]; then
	echo 'Test the instruction in vanilla PokeEMU mode'
	./run-testcase-offline.sh -m 0 -in $out/state-explr -out $out/single/ -e $emu_path
	./run-testcase-offline.sh -kvm -in $out/state-explr -out $out/single/
fi

if [ "$clean" == true ]; then
	rm -rf $out/state-explr $out/aggreg_list $out/single-m3
fi

