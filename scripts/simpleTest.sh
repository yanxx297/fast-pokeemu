#! /bin/bash
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
	echo -e "\e[1mState files alreay exist for $insn, skip machine state exploring...\e[21m"
	cp -r ../data/state-explr/$insn $out/state-explr/$insn
else
	echo -e "\e[1mMachine states for $insn absent. Start regeneration...\e[21m"
	cd ../tools/emuFuzzBall
        echo -e "\e[2m"
	python run-emu-fuzzball.py ../WhiteBochs-old/fuzzball-whitebochs ../../base.snap $shellcode $out/state-explr/$insn
        echo -e "\e[22m"
	cd -
fi

if [ -d ../data/state-explr/$insn ] && ( [ -d ../data/aggreg_list/$insn ] || [ "$aggreg" == false ]); then
	echo -e "\e[1mNo need to regenerate aggregation list.\e[21m"
	cp -r ../data/aggreg_list/$insn $out/aggreg_list/
else
	echo -e "\e[1mPrerun tests to regenerate aggregation list...(may take a while)\e[21m"
	./run-testcase-offline.sh -m 3 -in $out/state-explr -out $out/single-m3/ -e $emu_path
	./run-testcase-offline.sh -kvm -in $out/state-explr -out $out/single-m3/
	mkdir $out/aggreg_list/$insn
	for file in $out/single-m3/$insn/*.diff; do
		echo $out/state-explr/$insn/$(basename $file .diff)/testcase >> $out/aggreg_list/$insn/log
	done
	var=$(tr "\n" "," < $out/aggreg_list/$insn/log)
	echo ${var::-1} > $out/aggreg_list/$insn/log
	python split_log.py $out/aggreg_list/$insn/log 600
	rm $out/aggreg_list/$insn/log 
fi

if [ "$aggreg" == true ]; then
	echo -e "\e[1mTest the instruction in Fast PokeEMU mode\e[21m"
	./run-testcase-offline.sh -aggreg -m 3 -in $out/aggreg_list/ -out $out/aggreg/ -e $emu_path
	./run-testcase-offline.sh -kvm -in $out/state-explr -out $out/aggreg/
        echo -e "\e[1m"
        if [ -e $out/aggreg/$insn/mismatch ]; then
                echo -e "This aggregation \e[31mmismatches\e[39m."
        elif ! [ -e $out/aggreg/$insn/mismatch ] && [ -e $out/aggreg/$insn/match ]; then
                echo -e "This aggregation \e[31mmatches\e[39m."
        else
                echo "Fail to run the full experiment." 
                echo "Make sure you are using modified KVM kernel module for Fast PokeEMU."
        fi
        echo -e "\e[21m"
elif [ "$aggreg" == false ]; then
	echo -e '\e[1mTest the instruction in vanilla PokeEMU mode\e[21m'
	./run-testcase-offline.sh -m 0 -in $out/state-explr -out $out/single/ -e $emu_path
	./run-testcase-offline.sh -kvm -in $out/state-explr -out $out/single/
        echo -e "\e[1m"
        echo "For the $(echo "$(cat $out/single/$insn/match| wc -l)+$(cat $out/single/$insn/mismatch| wc -l)"| bc) tests in $insn"
        if [ -e $out/single/$insn/match ] && ! [ -e $out/single/$insn/mismatch ]; then
                echo -e "all of them \e[31mmatch\e[39m"
        elif ! [ -e $out/single/$insn/match ] && [ -e $out/single/$insn/mismatch ]; then
                echo -e "all of them \e[31mmismatch\e[39m"
        else
                echo "$(cat $out/single/$insn/match| wc -l) match, and $(cat $out/single/$insn/mismatch| wc -l) mismatch"
        fi
        echo -e "\e[21m"
fi

if [ "$clean" == true ]; then
	rm -rf $out/state-explr $out/aggreg_list $out/single-m3
fi

