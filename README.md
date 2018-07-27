# Fast PokeEMU

Fast PokeEMU is the successor of [PokeEMU](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.225.5080&rep=rep1&type=pdf) 
which integrates testcase aggregation, random testing and additional techniques for space saving.
More design details and experiment results of Fast PokeEMU are in
[our VEE 2018 paper](http://www-users.cs.umn.edu/~yanxx297/vee18-fast-pokeemu.pdf).

If you have any questions about building or using this tool, feel free to file an issue or contact Qiuchen Yan at yanxx297@umn.edu

PokeEMU and Fast PokeEMU are based in part on KEmuFuzzer, which was
created by Lorenzo Martignoni, Roberto Paleari, and Giampaolo Fresi
Roglia, advised by Danilo Bruschi. The original PokeEMU tool was
primarily the work of Lorenzo Martignoni, based on Stephen McCamant's
FuzzBALL, in joint research with Pongsin Poosankam, Dawn Song, and
Petros Maniatis. The Fast PokeEMU enhancements and other more recent
changes were primarily by Qiuchen Yan, advised by Stephen McCamant. We
appreciate the previous authors' contributions, but since they aren't
responsible for any recent changes, your probably shouldn't bother
them with bug reports.

Fast PokeEMU is free software. You may redistribute and/or modify it
under the terms of the GNU General Public License (GPL) version 3 as
published by the Free Software Foundation. This is the intersection of
the licenses of KEmuFuzzer (GPL 3) and FuzzBALL (GPL 2+). This
software is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details. You should have received a
copy of the GNU General Public License along with this program, in the
file COPYING.  It can also be obtained from the [GNU
Project](http://www.gnu.org/licenses/).

## Table of contents
- [Build Fast PokeEMU](#build)
- [Testing QEMU](#testing-qemu)
	- [A simple example](#simple-example)
	- [Effectiveness Experiment](#effectiveness-experiment)
	- [Details](#details-of-fast-pokeemu)
		- [Instruction Exploring](#instruction-exploring)
		- [Machine State Exploring](#machine-state-exploring)
		- [Test Case Execution](#test-case-execution)
		- [Compare Machine States](#compare-machine-states)
- [Historical Bug Experiment](#historical-bug-experiment)


## Build Fast PokeEMU
The Fast PokeEMU tool consists of several components, each of which has its own building process.
For simplicity, we include the binaries for all those components.
You may still want to check [KVM setup](#KVM) since it requires a specific version of Linux Kernel to run the kernel module we compiled.

If you are looking at this file, you've found the place to download the Fast PokeEMU code from. Note that the Git repository uses submodules for some related packages, so after `git clone` you should also do:

```bash
git submodule init
git submodule update
```

#### FuzzBALL
Below is a summary of the [FuzzBALL installation document](tools/fuzzball/INSTALL).
More details can be found in the original document, including a full list of required packages.
Most dependencies required by FuzzBALL are available as packages, but you have to compile VEX and STP.

For STP, download version r1673 from SVN repository and apply the corresponding patch.
When compilation finishes, copy the stp binary and libstp.a to tools/fuzzball/stp.
(Alternatively, you can also use an `stp` binary o the latest version from the STP Git repository.)

```bash
svn co -r1673 https://svn.code.sf.net/p/stp-fast-prover/code/trunk/stp stp-r1673+vine
cd stp-r1673+vine
patch -p0 <$HERE/stp/stp-r1673-true-ce+bison3.patch
./clean-install.sh --with-prefix=$(pwd)/install
cp install/bin/stp install/lib/libstp.a $HERE/stp
```

Instructions for compiling VEX are as below.

```bash
svn co -r2737 svn://svn.valgrind.org/vex/trunk vex-r2737
# You may need to apply one of those vex-* patches in tools/fuzzball
cd vex-r2737
make -f Makefile-gcc
```

After that, follow the instructions below to compile vanilla FuzzBALL in [tools/fuzzball/](tools/fuzzball/).
Note that you should tell the location of VEX to FuzzBALL using configure option.

```bash
./autogen.sh
./configure --with-vex=<path/to/vex/folder> 
make
```

To compile the enhanced version of FuzzBALL required by Fast PokeEMU, switch to [tools/emuFuzzBall/](tools/emuFuzzBall/) and run `make`.
You can find a binary named `emu_fuzzball` if the compilation succeeded.

PokeEMU's version of FuzzBALL uses [Z3](https://github.com/Z3Prover/z3) as its default solver.
Before you can use emu_fuzzball, make sure you compile Z3.

```bash
python scripts/mk_make.py
cd build
make
```

#### WhiteBochs
Simply run `make` in [tools/WhiteBochs-old/](tools/WhiteBochs-old/).

For compatibility with our scripts, (White)Bochs needs to be compiled
as a 32-bit binary. On x86-64 Debian or Ubuntu systems, we recommend
installing the `gcc-multilib` and `g++-multilib` packages to ensure
that a working 32-bit compiler and headers are available.

#### Pyxed
[Pyxed](https://github.com/huku-/pyxed) is a python wrapper around [Xed](https://github.com/intelxed/xed) library
We include Pyxed, Xed and its dependency (mbuild) as submodules.
Compile Xed first, then apply our patch `pyxed.patch` to pyxed and compile pyxed.

```bash
cd tools/xed
./mfile.py --shared install
cd ../tools/pyxed
patch -p1 < ../pyxed.patch
make
```

#### QEMU
To test QEMU using Fast PokeEMU, you must patch QEMU to support specific a format of memory dump used by (Fast) PokeEMU.
We have already ported this patch to a range of QEMU versions (1.0 - 2.21), and include those patched QEMUs in Fast PokeEMU as a submodule. 
```bash
cd emu/qemu
# check-qemu.sh compiles various versions of QEMU.
# You can also compile QEMU manually.
cp ../check-qemu.sh .
./check-qemu.sh
```

#### KVM
To run Fast PokeEMU testcases on KVM, you need a customized KVM kernel module and the software interface.

The software interface is in [emu/kvm-run](emu/kvm-run), 
simply run `make` to build it.

To build the KVM kernel module, download the Linux kernel source code, apply the patch `kvm_kmod_*.patch` corresponding to your kernel version and recompile it.
Currently we have patches for linux kernel 4.4, 4.13 and 4.16; we used kernel 4.4 for the experiments described in the paper.
It should also be possible to make an analogous change to any other version of the Linux kernel source code.
```bash
cd Linux-4.4
patch -p1 < ../Linux_4.4.0-45.66.diff
patch -p1 < ../kvm_kmod.diff
cp /boot/config-$(uname -r) .config
make oldconfig
make
```
Alternatively, you can use the KVM kernel modules we compiled for Linux 4.4.0-45.
They are in `kvm.ko` and `kvm-intel.ko` in [/emu](emu).
Note that in this case you must switch your current kernel to the same version. 

After that, either copy kvm.ko and kvm-intel.ko to `/lib/modules/$(uanme -r)/kernel/arch/x86/kvm` and reboot, or reload them as below.
Note that to remind you that their behavior is incompatible, the vanilla KVM'S API version is 12, while the modified KVM uses 2411.
```bash
cd Linux-4.4/arch/x86/kvm
rmmod kvm-intel
rmmod kvm
insmod kvm.ko
insmod kvm-intel.ko
# You can also use scripts/kmod.sh to switch between kernels
```

Depending in your Linux distribution, you may also need to make a
configuration change to give a user permission to use KVM, such as by
adding them to a group named `kvm`.

## Testing QEMU
### Simple example
You can simply test one instruction using `simpleTest.sh`.
This script takes the hex string of an instruction as input, generate a set of tests, and runs those tests either one by one (vanilla PokeEMU stylec turned on by `--single-test`) or at once (Fast PokeEMU style cturned on by `--aggreg-test`.)
For more details about each step of Fast PokeEMU, see [the next section](#details-of-fast-pokeemu).

In Fast PokeEMU mode, you may see the script rerun single tests to generate a list of valid tests to aggregate.
This is due to the incompleteness of PokeEMU's exception handler.
Note that in practice this is a one-time effort as long as you don't [regenerate machine states](#machine-state-exploring) or redo any other previous steps.

As a example, we run Fast PokeEMU tests for `add %al,(%eax)` using this one-line command.
```bash
./simpleTest.sh -s \\x00\\x00 --aggreg-test
# 00 00 is the hex string format of add %al,(%eax)
```
Alternatively, you can replace `--aggreg-test` with `--single-test` to test this instruction using vanilla PokeEMU.
For a full list of options, run `./simpleTest.sh -h`.

You can test any instruction by replacing `\\x00\\x00` with either strings from the 1st column of `instruction.csv` 
(remember to replace `\` with `\\`), 
or the hex string of any other valid Intel X86 instruction.

Some other examples you can test quickly.

| Instruction | Hex string |
| ------- | --------- |
| btr	%eax,0x0 | \\\\x0f\\\\xb3\\\\x05\\\\x00\\\\x00\\\\x00\\\\x00 |
| bsf	(%eax),%ax | \\\\0x66\\\\0x0f\\\\0xbc\\\\0x00 |
| mov	%cr0,%eax | \\\\x3e\\\\x0f\\\\x22\\\\x00 |

### Effectiveness experiment

We use the phrase "effectiveness experiment" for experiments like the
one in [section 5.3 of the VEE'18
paper](http://www-users.cs.umn.edu/%7Eyanxx297/vee18-fast-pokeemu.pdf#subsection.5.3)
which compare the fault-finding performance of Fast PokeEMU to that of
vanilla PokeEMU.

You have a choice of two scripts for running effectiveness
experiments. `pokeEMU-offline.sh` is the script that we used to run
the experiments in the paper, while `effect-one-insn.pl` runs similar
experiments but in a different order that reduces the maximum amount
of disk space required.

#### Effectiveness experiments with `pokeEMU-offline.sh`

Before running `pokeEMU-offline.sh`, you need to [generate machine states](#machine-state-exploring) for all the instructions you want to involve if you haven't, and set the `$in` in `pokeEMU-offline.sh` to the directory of machine states.

When you are ready, run the following instruction to run the full experiment.
It takes at least 40 hours on a typical PC.
The final results of this experiment are stored in `$dir/out`, where `$dir` is another variable in `pokeEMU-offline.sh` that you can change.
```bash
./pokeEMU-offline.sh -s 0
# -s 0 starts from the very beginning.
# You call also start from the middle of this experiment.
# (See ./pokeEMU-offline.sh -h for more options.)
```

#### Effectiveness experiments with `effect-one-insn.pl`

The `effect-one-insn.pl` script runs all the parts of an effectiveness
experiment that pertain to a single instruction variant (byte
sequence). The script takes two arguments, an output directory and an
instruction byte sequence. For instance:
```bash
perl effective-one-insn.pl /tmp/effect-out 013f
```

It will write experimental results in the output directory and also in
a subdirectory of the output directory named after the instruction
variant, e.g. `/tmp/effect-out/ADD_EdGdM-013f`.

To run the experiment in parallel across multiple instructions, you
may find it convenient to run under a command like `xargs -n1 -P6`,
where the argument to -P is the number of jobs to run in parallel. For
instance:
```bash
cut -f1 data/insns | xargs -n1 -P6 perl scripts/effect-one-insn.pl /tmp/effect-out
```

In addition the following environment variables will affect the
behavior of the script if they are present:

`FUZZBALL_MAX_ITERATIONS`: (default 4096) maximum number of testcases
to generate for a single instruction variant. This is a significant
factor in the running time of experiments, so you may wish to set it
to a small value initially.

`TIMEOUT`: (default 10) maximum time, in seconds, to run one testcase.

`DISABLE_CLEAN`: if set, retains all of the intermediate files from
each run. Keeping these around can be useful for debugging, but all of
the intermediate results from a long experiment will require a large
amount of disk space.

### Details of Fast PokeEMU
This section is useful if you want to rerun all the tests by yourself, or build your own tool on top of Fast PokeEMU.

#### Instruction exploring
In this step, we collect a list of x86 instructions by symbolic execution of Bochs, and randomly select one instruction for each mnemonic.
The output is a set of instructions (1078 in total), each of which stands for a instruction variation defined in Bochs.
For more details, check section 3.2 of the [PokeEMU paper](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.225.5080&rep=rep1&type=pdf)

The first step is to explore the instruction decoder of Bochs symbolically. 
```bash
cd tools/emuFuzzBall
python run-fuzzball.py ../WhiteBochs-old/fuzzball-whitedisasm
```
You can set the environment variable `$FUZZBALL_OUTDIR` to control where the output goes.
The default location is `/tmp/fuzzball-fuzzball-whitedisasm-output`.

Next, collect instruction information (including mnemonic, shellcode, length and corresponding function in Bochs) by parsing the outputs of symbolic execution.
```bash
perl scripts/collect-p1-shellcode.pl /tmp/fuzzball-fuzzball-whitedisasm-output| \
./tools/WhiteBochs-old/whitedisasm-many
# Change /tmp/fuzzball-fuzzball-whitedisasm-output if you
# used a different location
```
Save the output of this script to a file for the next steps. 
`instruction.csv` is an example of this step's results.

The last step is to randomly select one instruction from each mnemonic, and store them in a file.
For example, you can redirect the list to a file named `insn` for future use.
```bash
python select_insn_rand.py > insn
# change '../data/instructions.csv' to the file you generated
```

#### Machine state exploring
With the shellcode of an instruction, you can generate a set of machine states by symbolically exploring the instruction interpreter of Bochs, each of which corresponds to a test case that can test a unique behavior of this instruction.
```bash
cd tools/emuFuzzBall/
python run-emu-fuzzball.py ../WhiteBochs-old/ fuzzball-whitebochs ../../base.snap \
<shellcode> <\path\to\output\dir>
```
The shellcode is in the format of `\\x__\\x__\\x__...` where each `__` is two hexadecimal digits denoting one byte.
Note that if the input shellcode is not a complete instruction, the actually instruction executed by bochs will be a mixture of the given shellcode and what left in baseline memory.

Use `runCPUexplr` if you want to generate states for multiple instructions.
By default, this Makefile reads instructions from a file named `insn`, and generate machine states for all of them in parallel.
Change `$FILE` if you want to read a different instruction list, and `$TMP` if you want a different output folder (`/tmp/out` is the default.)
```bash
cd tools/emuFuzzBall/
make -f runCPUexplr -j 6
```


#### Test case execution
In this step, we generate executable test cases from  machine states, and run them on both QEMU and KVM.
The test case generator `run_test_case.py` can create tests in a variety of styles, and execute the test case on QEMU.

The required argument required by this script are described as below.
###### testcase
The path to the `testcase` file(s) of one machine or multiple state(s).
If you pass multiple files, separate each file by `,` without whitespace.
###### timeout 
Timeout in seconds.
###### outdir
Output folder.
###### script
The path to a shell script that runs QEMU.
Use `run-testcase` for normal testing.
The `run-testcase-debug` variant generates a floppy disk image `floppy-dbg` and a log of executed instructions `/tmp/qemu.log`, which can be useful if you want to manually run the test on KVM later or want to do debugging.
Use `run-testcase-remote` if you want to connect QEMU to gdb remote debugging interface, which for instance will let you single-step execution of the testcase.

###### mode
Select the mode of the test case. 
See the table below for more details.
###### loop
Set how many times you want to repeat random testing.
If not set, each test only run once by default (equal to `loop:1`.)
As mentioned in the table below, this option only make sense in mode 3.

| Number | Mode | Aggregation Support | Random Testing |
| ------ | ------ | ------ | ------ |
| 0 | Vanilla PokeEMU | No | No |
| 1 | Simple aggregation | Yes | No |
| 2 | Feistel aggregation | Yes | No |
| 3 | Feistel aggregation with looping | Yes | Yes |

Here are some examples using this script.
```bash
# Single test in vanilla PokeEMU mode
python run_test_case.py testcase:../data/state-explr/ADD_EbGbM/00000000/testcase timeout:5 \
outdir:/tmp/out/ script:..emu/qemu/run-testcase mode:0
# An aggregation consists of multiple tests with 10000 iterations of random testing 
python run_test_case.py testcase:../data/state-explr/ADD_EbGbM/00000000/testcase, \
../data/state-explr/ADD_EbGbM/00000001/testcase,../data/state-explr/ADD_EbGbM/00000002/testcase  \
timeout:5 outdir:/tmp/out/ script:../emu/qemu/run-testcase mode:3 loop:10000
```
To manually run the KVM test, set `script` to `run-testcase-debug` when you generate the test.
After that, you will get the floppy disk image named `floppy-dbg`.
Use this image to rerun the QEMU test, so that you can get the `*.pre` file (which is the machine state before running this test.)
Finally, run the .pre file on KVM.
```bash
cd emu/qemu
./run-testcase /tmp/floppy-dbg /tmp/out/dbg.post /tmp/out
#./run-testcase </path/to/floppy-dbg> </path/to/*.post> </output/folder>
cd ../kvm-run
./run-testcase /tmp/out/dbg.post.pre /rmp/out/00000000-kvm.post
#./run-testcase </path/to/*.pre> </output/folder>
```

Alternatively, you can used `run-testcase-offline.sh` to run a set of instructions in parallel.
This script is a wrapper around `batchRunTestcase`, `batchRunAggregTC` and `batchRunTestcase-kvm-offline`, which execute single QEMU test (default), aggregation QEMU test (with option `-aggreg`) or KVM test (with option `kvm`), respectively.

#### Compare machine states
The final step is to compare the 2 memory dumps we got from KVM and QEMU. 
Memory dumps are represented as *.post files.
Any two dumps can be compared, and diff_cupstate.py can tell whether a dump is generated by Bochs, QEMU or KVM.
```bash
cd scripts
python diff_cpustate.py /tmp/out/dbg.post.post /tmp/out/00000000-kvm.post
#python diff_cpustate.py </path/to/QEMU/memdump> </path/to/KVM/memdump>
```
When you run diff_cpustate.py with only one memory dump, it will print the most important fields of the dumped CPU state.
This information can be very helpful for debugging.

## Historical bug experiment
Another experiment mentioned in the paper is to identify real world QEMU bugs, and evaluate the ability of random testing to find those bugs.
This script first does a round of pre-running to select tests that reveal bugs on the earliest version of QEMU but reveal nothing (pass) on the most recent version (likely because a bug has been fixed).
It then uses each of those tests to identify the git commit that fixes this bug by performing a binary search among a range of QEMU versions.
For more details about the historical bug experiment, see the [relevant section](http://www-users.cs.umn.edu/~yanxx297/vee18-fast-pokeemu.pdf#subsection.5.4) in Fast PokeEMU paper.

Similar to the [effectiveness experiment](#effectiveness-experiment), you need to set `$in` to a machine states directory, and `$out` to an output directory.
(Alternatively, you can set the input using ``-in``.)
In addition, copy the aggregation list folder (named `aggreg_list`) generated in the effectiveness experiment to `$out`.
After that, run the following command to run the historical bug experiment for vanilla PokeEMU and Fast PokeEMU with 10000 loop iterations, or customize your own experiment with different setup.
```bash
./historical.sh -in ../data/state-explr -m 0
./historical.sh -in ../data/state-explr -m 3 -i 10000
# -in <path/to/machine_states> 
# -m <mode> -i <loop-iteration>
```
By default, this script selects tests by running all the tests one by one, check the comparison result on earliest and latest QEMU for each test, and selects those tests that mismatch on earliest and match on latest QEMU.
To speed up this process, you can run an aggregation of those tests for each instruction by turning on the option `--aggreg`.
Note that by taking this approach you will miss some valid tests for binary search if the aggregation includes tests that reveal multiple bugs.

For example, commit [321c535](https://github.com/qemu/qemu/commit/321c535) fixes the undefined zero flag of the bsf instruction according to a recent change in Intel specification, but the behavior of the parity flag is still undefined in both QEMU and the specification.
In other words, QEMU and KVM may have inconsistent behavior on the parity flag, which has been triggered by some tests we generated.
As a result, if you include those tests in the aggregation (there is no way to identify those tests without running all the tests separately), the testing result of this aggregation will be mismatch in both earliest and latest QEMU, even if the zero flag bug has been fixed in the latest version.

Not all the commits identified by this experiment are fixes to real bugs.
In other words, there are false positives in the result the historical bug experiment.
Most false positives results are caused by randomness of Fast PokeEMU, but our patch searching approach can also fail if there are two or more bugs overlapping in the same range.
For the former case, we can exclude those results by rerunning part of the experiment several times, and only trust results that are consistent among every execution.
[repeat-hisbug.sh](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/scripts/repeat-hisbug.sh)
and [repeat-run-testcase.sh](https://github.umn.edu/yanxx297/fast-pokeemu/tree/master/scripts/repeat-run-testcase.sh)
are two examples of false positive filtering.

It is challenging to exclude false positive results caused by the latter reason, but as far as we know there are only 2 instructions in this group: MOVQ_PqQqM and RDMSR.
For those two instructions, the bug leads to behavior difference overlaps with another bug that stop our tests from running (which we call a `fatal bug`.)
As a result, our binary search approach always stop on the patch that fixes the fatal bug.
As long as we cannot exclude the fatal bug, there is no way to identify the fix to behavior difference bug.
This is a drawback of our current design, and improving the search approach can be our future work.

After excluding all false positives, the result of historical bug experiment is as below.

| Fix | Instruction | Without random testing | With random testing |
| ------ | ------ | ------ | ------ |
| [321c535](https://github.com/qemu/qemu/commit/321c535) | BSF_GdEdR<br> BSR_GdEdR| Yes<br> Yes | Yes<br> Yes |
| [dc1823c](https://github.com/qemu/qemu/commit/dc1823c) | BTR_EdGdM<br>BTR_EdGdR<br>BTR_EdIbM<br>BTR_EdIbR<br>BTR_EwGwM<br> BTC_EdGdM<br> BTC_EdGdR<br> BTC_EdIbM<br> BTC_EdIbR<br> BTC_EwGwM<br> BT_EdGdM<br>BT_EdGdR<br>BT_EdIbM<br>BT_EdIbR<br>BT_EwGwM<br> BTS_EdGdM<br>BTS_EdGdR<br>BTS_EdIbM<br>BTS_EdIbR<br>BTS_EwGwM| Yes<br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br><br> | Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes<br>Yes |
| [5c73b75](https://github.com/qemu/qemu/commit/5c73b75) | MOV_CdRd<br> MOV_DdRd<br> MOV_RdCd<br> MOV_RdDd| Yes<br>Yes<br>Yes<br>Yes<br> | Yes<br>Yes<br>Yes<br>Yes<br> |
