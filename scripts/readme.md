# Useful scripts

Check script files for usage of those scripts.

#### select_insn_rand.py
Given the Instruction.csv, randomly choose one instruction from each class.

#### batch_run_test_case.sh
Run all the test cases in a folder.

#### barchRunTestcase
Makefile version of batch_run_test_case.sh.
In addition, it can run test cases of all instructions instead of one instruction.

#### batchRunTestcase-kvm
Similar to barchRunTestcase, but for KVM execution.

#### batchRunAggregTC
For each instruction, take a list of test cases and run the aggregation of them.
This makefile works for both QEMU and KVM execution.

#### aggreg_test_case.sh
Given a directory containing the outputs of CPU state exploring
(fuzzball-output by default),
return a of paths to each 'testcase' file.
Paths separated by comma.

#### aggreg_tc_from_dump.sh
Given a directory containing outputs of test case executing,
check each .post memory dump to figure out whether the corresponding test case terminate with an exception.<br>
Return a list of test cases halted normally.

#### aggreg_tc_from_2dumps.sh
Similar to aggreg_tc_from_dump.sh but generate test case list according to 2 groups of.post files in different folders,
usually one for QEMU and another for KVM.

#### wrapper_diff_cpustate.sh
A wrapper for diff_cpustate.py to compare 2 groups of memory dumps.

#### wrapper_aggreg_tc_from_dump.sh
A wrapper for aggreg_tc_from_2dumps.sh/aggreg_tc_from_dump.sh to generate non-exception test case lists for a group of instructions.

#### diff_aggreg.sh
Given the .diff files of single test cases and aggreg test cases, this script generate categorize all the instructions into 4 classes: both mismatch, both match, only aggreg mismatch and only separate mismatch.
Outputs are 4 lists contained in 4 files.  
00000000.diff contains an example of diff_cpustate.py's output when the 2 memory dumps are equivalent.

#### tools/emuFuzzBALL/run-CPU-explr.sh
Given a list of instructions (in shellcode format)
run each of them, and locate the results in a directory named after instruction name.
