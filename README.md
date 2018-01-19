# Pokemu-Oras

This repository includes the most essential part of new Pokemu.

- FuzzBALL-for-Pokemu based on a recent version of FuzzBALL
- Whitebochs
- Scripts & files

This repository doesn't include the following 

- Vanilla FuzzBALL
- Original FuzzBALL-for-Pokemu 
- Emulators for testing and comparison (Various QEMUs and KVM)
	- Please put them in emu/ 


Compilation
-----------------------
1. Compile tools/fuzzball
2. Download [z3-2.15](http://research.microsoft.com/en-us/um/redmond/projects/z3/z3-x64-2.15.tar.gz), add "Z3_OP_FD_LE," to z3/include/z3_api.h, one line after "Z3_OP_FD_LT,"
  build the OCaml interface according to z3/ocaml/README.
3. Compile tools/emuFuzzBall with **make** 
4. Clone the [Pyxed](https://github.com/huku-/pyxed.git) submodule, and download [Intel Pin library](https://software.intel.com/en-us/articles/pin-a-dynamic-binary-instrumentation-tool). 
Apply pyxed.patch to Pyxed Makefile before compiling.

Instruction Exploring
-----------------------
### symbolic execution
Run symbolic execution with 3 symbolic instruction bytes as input. 
This step uses fuzzball-whitedisasm.

	cd ~/Project/pokemu-oras/tools/emuFuzzBall
	python run-fuzzball.py ../WhiteBochs-old/fuzzball-whitedisasm

You can set the environment variable $FUZZBALL_OUTDIR to control where
the output goes; the default location is /tmp/fuzzball-fuzzball-whitedisasm-output

### concrete execution
Given the testcases generated in step 1, run them with a concrete
Bochs to collect information like their length, disassembly, and Bochs
implementation function.

The newer and faster way of doing this uses a Perl script to collect
all the instruction bytes, and runs them all through a single
execution of a program named "whitedisasm-many". The results go to the
standard output so you can name them whatever you want. For instance:

	perl scripts/collect-p1-shellcode.pl
           /tmp/fuzzball-fuzzball-whitedisasm-output |
        ./tools/WhiteBochs-old/whitedisasm-many >instructions.tsv

The older approach used shell scripts and a program
concrete-whitedisasm which ran separately for each instruction, and
stored its results in .../scripts/instructions.csv:
	cd ~/Project/pokemu-oras/scripts
	./run_analyze_shell_code.sh /tmp/fuzzball-fuzzball-whitedisasm-output/

Notes:
- Uncomment lines after "#For disasm" in scripts/commcon.py
- Don't print anything in load_fuzzball_tc (in common.py) because the output of this function is the input to concrete-whitedisasm



Machine State Exploring
-----------------------

In tools/emuFuzzBall-old/, run the following command:

	python run-emu-fuzzball.py
	/home/yanxx297/Project/pokemu-oras/tools/WhiteBochs-old/fuzzball-whitebochs 
	/home/yanxx297/Project/pokemu-oras/base.snap <shellcode>

The shellcode is in the format of \\x__\\x__\\x__ ... where each __ is one byte(2 letters).
Note that if the input shellcode is not in full length, the actually instruction executed by bochs will be a mixture of the given shellcode and what left in inital memory.

To run old binaries, replace *emu_fuzzball* with *emu_fuzzball_old* in run-emu-fuzzball.py, and run this command:

	python run-emu-fuzzball.py 
	/home/yanxx297/Project/pokemu-oras/tools/WhiteBochs-old/fuzzball-whitebochs-old 
	/home/yanxx297/Project/pokemu-oras/base.snap <shellcode>



Test Case Execution
------------------------------

### Build customized KVM
To run pokemu testcases on kvm, a customized kvm module is required.
This folder include the old version customized kvm (2.6.37), a more recent version of customized kvm(3.16, with a patch generated by comparing vanilla kvm 3.16 with the modified one) and the vanilla version of them.
NOTE: you must compile kvm on the machine on which you will run kvm.

To build kvm, follow the README in kvm-kmod-* folders.
After that you will get three kernel modules: kvm.ko, kvm-intel.ko and kvm-amd.ko
Copy them to /lib/modules/$(uanme -r)/kernel/arch/x86/kvm and restart, so that OS will load them at startup.
Note that vanilla kvm's api version is 12, while the modified kvm is 2411.


### Run other emulators
Use the run-testcase in each emulator's folder to run them.
You can find hint about running each run-testcase in emu/run-testcases
e.g. for qemu-0.12.4+dfsg, the cmd is: 

	python run_test_case.py testcase:/path/to/testcase timeout:5
	outdir:/tmp/out/ script:/emu/qemu-0.12.4+dfsg/run-testcase

For example: 

	python run_test_case.py testcase:/tmp/00/00000001/testcase,
	/tmp/00/00000000/testcase timeout:5 outdir:/tmp/out/
	script:/emu/qemu-0.12.4+dfsg/run-testcase

Notes:
- run-testcase call functions in gen_floppy_image.py to generate floppy disk, which include all the content of kernel disk.
- Must run on (software based) emulators first to generate the *.pre file, which is the input of kvm.


### Run test cases on kvm
kvm-run/ includes code running testcases on kvm. This code interacts with kvm by api.
To run kvm-run, simply enter the emu/kvm-run directory and run the following cmd:

	./run-testcase /path/to/*.pre /output/folder

Note that the testcase is already included in the *.pre file.



Testcase Generation
--------------------

Regenerate testcases from result of machine state exploring.
command line:
		
	perl regen-testcases.pl <folder name of machine state exploring results>

Before running this script, must uncomment lines in /scripts/common.py after "#For testcase generation"

To regen single testcase:

	python gen_floppy_image.py debug:2 testcase:/path/to/testcases kernel:kernel-base floppy:floppy-base

Note that this step is not included in the working flow of Pokemu.
The goal of this step is to REgenerate testcases, while the regenerated testcases are used in nowhere.  



Comparing Machien State Dumps
------------------------------------------

Enter scripts/ and run the following command:

	python diff_cpustate.py /path/to/memdump1 /path/to/memdump2

memory dumps are *.post files.
Any two dumps can be compared, and diff_cupstate.py can tell whether it's generated by Bochs, QEMU or kvm
Result can be read in the following way:
| text Color| Meanintg	|
|-------|:---------:|
| Green | the same	|
| Yellow| different	|
| Red 	| invalid dumps|

