# Fast PokeEMU

Fast PokeEMU is the successor of [PokeEMU](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.225.5080&rep=rep1&type=pdf) 
which integrate testcase aggregation, random testing and additional technique for space saving.
More design details and experiment results of Fast PokeEMU are in
[this paper](http://www-users.cs.umn.edu/~yanxx297/vee18-fast-pokeemu.pdf). 

## Table of contents
- [Build Fast PokeEMU](#build)
- [Testing QEMU](#testing-qemu)
	- [A simple example](#simple-example)
	- [Effectiveness Experiment](#effectiveness-experiment)
	- [Details](#details-of-fast-pokeEMU)
		- [Instruction Exploring](#instruction-exploring)
		- [Machine State Exploring](#machine-state-exploring)
		- [Test Case Execution](#test-case-execution)
		- [Compare Machine States](#compare-machine-states)
- [Historical Bug Experiment](#historical-bug-experiment)


## Build Fast PokeEMU
The Fast PokeEMU consists of several components, each of which has its own building process.
For simplicity, we include the binaries for all components.
You may still want to check [KVM setup](#Build_KVM) since it requires a specific version of Linux Kernel to run the kernel module we compiled.

#### FuzzBALL
This is a simpified version of [FuzzBALL installation document](https://github.umn.edu/yanxx297/fast-pokeemu/blob/master/tools/fuzzball/INSTALL).
More details can be found in the original document, including a full list of required packages.
Most dependencies required of FuzzBALL are available as packages, but you have to compile VEX and STP.

For STP, download the certain version from SVN and apply the corresponding patch.
When compilcation finished, copy the stp binary and libstp.a to tools/fuzzball/stp

```bash
svn co -r1673 https://svn.code.sf.net/p/stp-fast-prover/code/trunk/stp stp-r1673+vine
cd stp-r1673+vine
patch -p0 <$HERE/stp/stp-r1673-true-ce+bison3.patch
./clean-install.sh --with-prefix=$(pwd)/install
cp install/bin/stp install/lib/libstp.a $HERE/stp
```

Instructions for compiling VEX are as bellow.

```bash
svn co -r2737 svn://svn.valgrind.org/vex/trunk vex-r2737
cd vex-r2737
make -f Makefile-gcc
```

After that, follow the instructions bellow to compile vanilla FuzzBALL in [tools/fuzzball/](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/tools/fuzzball/).
Note that you should tell the location of VEX to FuzzBALL using configure option.

```bash
./autogen.sh
./configure --with-vex=<path/to/vex/folder> 
make
```

To compile the modified version of FuzzBALL required by Fast PokeEMU , switch to [tools/emuFuzzBall/](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/tools/emuFuzzBall/) and run `make`.
You should find a binary named `emu_fuzzball` if succeed.

PokeEMU version FuzzBALL use [Z3](https://github.com/Z3Prover/z3) as its default solver.
Before you can use emu_fuzzball, make sure you compile Z3.

```bash
python scripts/mk_make.py
cd build
make
```

#### WhiteBochs
Simpily run `make` in [tools/WhiteBochs-old/](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/tools/WhiteBochs-old/).

#### Pyxed
Download [PIN](https://software.intel.com/en-us/articles/pin-a-binary-instrumentation-tool-downloads),
extract to [tools/](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/tools/) and rename the folder to `pin`.
After that, apply our patch `pyxed.patch` to pyxed and compile it.

	cd tools/pyxed
	patch -p1 < ../pyxed.patch
	make

#### QEMU
To test QEMU using Fast PokeEMU, QEMU must be patched to support specific format memory dump used by Fast PokeEMU.
We already port this patch to a range of QEMU versions (1.0 - 2.21), and include those patched QEMUs in Fast PokeEMU as a submodule. 

	cd emu/qemu
	cp ../check-qemu.sh .
	./check-qemu.sh

#### KVM
To run Fast PokeEMU testcases on kvm, you need a customized KVM kernel module and the software interface.

The software interface is in [emu/kvm-run](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/emu/kvm-run), 
simply run `make` to build it.

To build the KVM kernel module, you need to download linux kernel source code, apply the patch `kvm_kmod.patch` and recompile it.
Though it is possible to apply the patch to any linux kernel source code, we only have tested it on
[linux 4.4.0-45.66 in Ubuntu](https://launchpad.net/ubuntu/+source/linux/4.4.0-45.66), which is the environment we used for all the experiments described in the paper.

	cd Linux-4.4
	patch -p1 < ../Linux_4.4.0-45.66.diff
	patch -p1 < ../kvm_kmod.diff
	cp /boot/config-$(uname -r) .config
	makd oldconfig
	make


Alternatively, you can use the KVM kernel modules we compiled for Linux 4.4.0-45.
They are in `kvm.ko` and `kvm-intel.ko` in [/emu](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/emu).
Note that in this case you must switch your current kernel to the same version. 

After that, either copy kvm.ko and kvm-intel.ko to `/lib/modules/$(uanme -r)/kernel/arch/x86/kvm` and reboot, or reload them as bellow.
Note that vanilla kvm's api version is 12, while the modified kvm is 2411.

	cd Linux-4.4/arch/x86/kvm
	rmmod kvm-intel
	rmmod kvm
	insmod kvm.ko
	insmod kvm-intel.ko

## Testing QEMU
### Simple example
You can simply test one instruction using `simpleTest.sh`.
This script takes the hex string of an instruction as input, generate a set of tests, and runs those tests either one by one (vanilla PokeEMU style turned on by `--single-test`) or at once (Fast PokeEMU style turned on by `--aggreg-test`.)
For more details about each step of (Fast) PokeEMU, see [the next section](#full-test).

In Fast PokeEMU mode, you may need to rerun single tests to generate a list of valid tests to aggregate.
This is due to the incompletenes of PokeEMU's exception handler.
Note that in practice this is a one-time effort as long as you don't [regenerate machine states](#machine-state-exploring) or redo any other previous steps.

As a example, we run Fast PokeEMU tests for `add %al,(%eax)` using this one-line command.
```bash
./simpleTest.sh -s \\x00\\x00 --aggreg-test
# 00 00 is the hex string format of add %al,(%eax)
```
Alternatively, you can replace `--aggreg-test` with `--single-test` to test this instruction using vanilla PokeEMU.
For a full list of options, run `./simpleTest.sh -h`.

You can test any instruction by replacing `\\\\x00\\\\x00` with any string from the 1st column of `instruction.csv` 
(remember to replace `\\` with `\\\\`), 
or the hex string of any other valid Intel X86 instruction.

Some other examples you can test quickly.
| Instruction | Hex string |
|-------|:---------:|
| btr	%eax,0x0 | \\\\x0f\\\\xb3\\\\x05\\\\x00\\\\x00\\\\x00\\\\x00 |
| bsf	(%eax),%ax | \\\\0x66\\\\0x0f\\\\0xbc\\\\0x00 |
| mov	%cr0,%eax | \\\\x3e\\\\x0f\\\\x22\\\\x00 |

### Effectiveness experiment
Another useful script is `pokeEMU-offline.sh`, which runs the [effectiveness experiment](http://www-users.cs.umn.edu/%7Eyanxx297/vee18-fast-pokeemu.pdf#subsection.5.3) automatically.
Before running this script, you need to [generate machine states](#machine-state-exploring) for all the instructions you want to involve if you haven't, and set the `$in` in `pokeEMU-offline.sh` to the directory of machine states.

When you are ready, run the following instruction to run the full experiment.
It takes around 40 hours on a normal PC.
The final results of this experiment are stored in `$out\out`, where `$out` is another variable in `pokeEMU-offline.sh` that you can change.
```bash
./pokeEMU-offline.sh -s 0
# -s 0 starts from the very beginning.
# You call also start from the middle of this experiment.
# (See ./pokeEMU-offline.sh -h for more options.)
```

### Details of Fast PokeEMU
This section is useful if you want to rerun all the tests by yourself, or build your own tool on top of Fast PokeEMU.

#### Instruction exploring
This step collect a list of x86 instructions by combining symbolic and concolic execution of Bochs, and randomly select one instruction from each mnemonic.
The output is 1078 instructions, each of which stands for a instruction variation defined in Bochs.
For more details, check section 3.2 of the [PokeEMU paper](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.225.5080&rep=rep1&type=pdf)

The first step is to explore the instruction decoder of Bochs symbolically. 
```bash
cd tools/emuFuzzBall
python run-fuzzball.py ../WhiteBochs-old/fuzzball-whitedisasm
```
You can set the environment variable `$FUZZBALL_OUTDIR` to control where the output goes.
The default location is `/tmp/fuzzball-fuzzball-whitedisasm-output`.

Next, collect instruction indormation (including mnemonic, shellcode, length and corresponding function in Bochs) by parsing the outputs of symbolic execution.
```bash
perl scripts/collect-p1-shellcode.pl /tmp/fuzzball-fuzzball-whitedisasm-output| \
./tools/WhiteBochs-old/whitedisasm-many
# Change /tmp/fuzzball-fuzzball-whitedisasm-output if you 
```
Save the output of this script to a file for the next steps. 
`instruction.csv` is an example of this step.

The last step is to randomly select one instruction from each mnemonic, and store them in a file.
For example, you can redirect the list to a file named `insn` for future use.
```bash
python select_insn_rand.py > insn
# change '../data/instructions.csv' to the file you generated
```

#### Machine state exploring
With the shellcode of an instruction, you can generate a set of machine states by symboliccally exploring the instruction interpreter of Bochs, each of which corresponds to a test case that can test a unique behavior of this instruction.
```bash
cd tools/emuFuzzBall/
python run-emu-fuzzball.py ../WhiteBochs-old/ \
fuzzball-whitebochs ../../base.snap <shellcode> \
<\path\to\output\dir>
```
The shellcode is in the format of `\\x__\\x__\\x__...` where each __ is one byte (or 2 letters corresponding to a hexadecimal value.)
Note that if the input shellcode is not in full length, the actually instruction executed by bochs will be a mixture of the given shellcode and what left in inital memory.

Use `runCPUexplr` if you want to generate states for multiple instructions.
By default, this Makefile read instructions from a file named `insn`, and generate machine states for all of them in paralle.
Change `$FILE` if you want to read a different instruction list, and `$TMP` if you want a different output folder (`/tmp/out` by default.)
```bash
cd tools/emuFuzzBall/
make -f runCPUexplr -j 6
```


#### Test case execution
In this step, we generate executable test cases from  machine states, and run those tests on both QEMU and KVM.

The test case generator `run_test_case.py` can create tests in a variey of styles, and execute the test case on QEMU.
This script requires several arguments. 
###### testcase
The path to the `testcase` file(s) of one machine or multiple state(s).
If you pass multiple files, connect each file by `,`.
###### timeout 
Timeout in second.
###### outdir
Output folder.
###### script
The path to a shellscript that runs QEMU.
Use `run-testcase` for normal testing.
The `run-testcase-debug` generate a floppy disk image `floppy-dbg` and a log of executed instructions `qemu.log` in `/tmp`, use this script if you want to manually run the test one KVM later or want to do debugging.
Use `run-testcase-remote` if you want to connect QEMU to gdb remotely for further debugging.
###### mode
Select the mode of the test case. 
See the table bellow for more details.
###### loop
Set how many times you want to repeat random testing.
If not set, each test only run once by default (equal to loop:1.)
As mentioned in the table bellow, this option only make sense in mode 3.
| Number | Mode | Aggregation Support | Random Testing |
| ------ | ------ | ------ | :------:|
| 0 | Vanilla PokeEMU | No | No |
| 1 | Simple aggregation | Yes | No |
| 2 | Feistel aggregation | Yes | No |
| 3 | Feistel aggregation with looping | Yes | Yes |

Some sxamples using this script 
```bash
# Single test in vanilla PokeEMU mode
python run_test_case.py testcase:../data/state-explr/ADD_EbGbM/00000000/testcase timeout:5 \
outdir:/tmp/out/ script:..emu/qemu/run-testcase mode:0
# An aggregation consists of multiple tests with 10000 times random testing 
python run_test_case.py testcase:../data/state-explr/ADD_EbGbM/00000000/testcase, \
../data/state-explr/ADD_EbGbM/00000001/testcase,../data/state-explr/ADD_EbGbM/00000002/testcase  \
timeout:5 outdir:/tmp/out/ script:../emu/qemu/run-testcase mode:3 loop:10000
```
To manually run the KVM test, set `script` to `run-testcase-debug` when you generate the test.
After that, you will get the floppy disk image named `floppy-dbg`.
Use this image to rerun the QEMU test, so that you can get the `*.pre` file (which is the machine state before running this test), and run it on KVM.
```bash
cd emu/qemu
./run-testcase /tmp/floppy-dbg /tmp/out/dbg.post /tmp/out
#./run-testcase </path/to/floppy-dbg> </path/to/*.post> </output/folder>
cd ../kvm-run
./run-testcase /tmp/out/dbg.post.pre /rmp/out/00000000-kvm.post
#./run-testcase </path/to/*.pre> </output/folder>
```

Alternatively, you can used `run-testcase-offline.sh` to run a set of instructions in paralle.
This script is a wrapper around `batchRunTestcase`, `batchRunAggregTC` and `batchRunTestcase-kvm-offline`, which execute single QEMU test (default), aggregation QEMU test (with option `-aggreg`) or KVM test (with option `kvm`), respectively.

#### Compare machine states
The final step is to compared the 2 mempry dumps we got from KVM and QEMU. 
memory dumps are *.post files.
Any two dumps can be compared, and diff_cupstate.py can tell whether it's generated by Bochs, QEMU or KVM.
```bash
cd scripts
python diff_cpustate.py /tmp/out/dbg.post.post /tmp/out/00000000-kvm.post
#python diff_cpustate.py </path/to/QEMU/memdump> </path/to/KVM/memdump>
```

## Historical bug experiment
Another experiment mentioned in the paper is to identify real world QEMU bugs, and evaluate the impact of random testing using those bugs.
This script first do a round of prerun to identify tests that reveal bugs on the earlest version of QEMU, but reveal nothing on the most recent version, hopefully because this bug has been fixed.
It then use each of those tests to identify the git commit that fix this bug by performing a binary search among a range of QEMUs.
For more details about the historical bug experiment, see the [relevant section](http://www-users.cs.umn.edu/~yanxx297/vee18-fast-pokeemu.pdf#subsection.5.4) in Fast PokeEMU paper.

Similar to the [effectiveness experiment](#effectiveness-experiment), you need to set `$in` for machine states directory, and `$out` for output directory.
In addition, copy the aggregation list folder (named `aggreg_list`) generated in the effectiveness experiment to `$out`.
After that, run the following command to run the full experiment, or replace 0 with other numbers (1-4) to start from the middle.
```bash
./historical.sh -s 0
```