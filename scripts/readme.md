# Useful scripts

Check script files for usage of those scripts.

#### select_insn_rand.py
Given the Instruction.csv, randomly choose one instruction from each class.

#### batch_run_test_case.sh
Run all the test cases in a folder.

#### barchRunTestcase
Makefile version of batch_run_test_case.sh.
In addition, it can run test cases of all instructions instead of one instruction.

#### aggreg_test_case.sh
Given a directory containing the outputs of CPU state exploring
(fuzzball-output by default),
return a of paths to each 'testcase' file.
Paths separated by comma.

#### aggreg_tc_from_dump.sh
Given a directory containing outputs of test case executing,
check each .post memory dump to figure out whether the corresponding test case terminate with an exception.<br>
Return a list of test cases halted normally.

#### tools/emuFuzzBALL/run-CPU-explr.sh
Given a list of instructions (in shellcode format)
run each of them, and locate the results in a directory named after instruction name.
