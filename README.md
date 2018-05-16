# Fast PokeEMU

Fast PokeEMU is the successor of [PokeEMU](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.225.5080&rep=rep1&type=pdf) 
which integrate testcase aggregation, random testing and additional technique for space saving.
More design details and experiment results of Fast PokeEMU are in
[this paper](http://www-users.cs.umn.edu/~yanxx297/vee18-fast-pokeemu.pdf). 

## Table of Content
- [Build Fast PokeEMU](#Build)
- [Testing QEMU](#Testing_QEMU)
	- [A simple example](#Sample_Example)
- [Historical Bug Experiment](#Historical_Bug_Experiment)


## Build
The Fast PokeEMU consists of several components, each of which has its own building process.
For simplicity, we include the binaries for all components.
You may still want to check [KVM setup](#Build_KVM) since it requires a specific version of Linux Kernel to run the kernel module we compiled.

#### Build FuzzBALL-for-PokeEMU
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

After that, follow the instructions bellow to compile vanilla FuzzBALL in `tools/fuzzball/`.
Note that you should tell the location of VEX to FuzzBALL using configure option.

```bash
./autogen.sh
./configure --with-vex=<path/to/vex/folder> 
make
```

To compile the modified version of FuzzBALL required by Fast PokeEMU , switch to `tools/emuFuzzBall/` and run `make`.
You should find a binary named `emu_fuzzball` if succeed.

PokeEMU version FuzzBALL use [Z3](https://github.com/Z3Prover/z3) as its default solver.
Before you can use emu_fuzzball, make sure you compile Z3.

```bash
python scripts/mk_make.py
cd build
make
```

#### Build WhiteBochs
Simpily run `make` in `tools/WhiteBochs-old/`.

#### Build Pyxed
Download [PIN](https://software.intel.com/en-us/articles/pin-a-binary-instrumentation-tool-downloadsa),
extract to `tools/` and rename the folder to `pin`.
After that, apply our patch `pyxed.patch` to pyxed and compile it.

	cd tools/pyxed
	patch -p1 < ../pyxed.patch
	make

#### Build QEMU
To test QEMU using Fast PokeEMU, QEMU must be patched to support specific format memory dump used by Fast PokeEMU.
We already port this patch to a range of QEMU versions (1.0 - 2.21), and include those patched QEMUs in Fast PokeEMU as a submodule. 

	cd emu/qemu
	cp ../check-qemu.sh .
	./check-qemu.sh

#### Build KVM
To run Fast PokeEMU testcases on kvm, you need a customized KVM kernel module and the software interface.

The software interface is in `emu/kvm-run`, simply run `make` to build it.

To build the KVM kernel module, you need to download linux kernel source code, apply the patch `kvm_kmod.patch` and recompile it.
Though it is possible to apply the patch to any linux kernel source code, we only have tested it on
[linux 4.4.0-45.66 in Ubuntu](https://launchpad.net/ubuntu/+source/linux/4.4.0-45.66), which is the environment we used for all the experiments described in the paper.

	cd Linux-4.4
	patch -p1 < ../Linux_4.4.0-45.66.diff
	patch -p1 < ../kvm_kmod.diff
	cp /boot/config-$(uname -r) .config
	makd oldconfig
	make


Alternatively, you can used the KVM kernel modules we compiled for Linux 4.4.0-45.
Note that in this case we must switch your current kernel to the same version. 

After that, copy kvm.ko and kvm-intel.ko to `/lib/modules/$(uanme -r)/kernel/arch/x86/kvm` and reboot, or reload them as bellow.
Note that vanilla kvm's api version is 12, while the modified kvm is 2411.

	cd Linux-4.4/arch/x86/kvm
	rmmod kvm-intel
	rmmod kvm
	insmod kvm.ko
	insmod kvm-intel.ko

## Testing QEMU
### Simple Example
### Detailed Instruction
#### Instruction Exploring
Run symbolic execution with 3 symbolic instruction bytes as input.
This step uses fuzzball-whitedisasm.

	cd ~/Project/pokemu-oras/tools/emuFuzzBall
	python run-fuzzball.py ../WhiteBochs-old/fuzzball-whitedisasm

You can set the environment variable $FUZZBALL_OUTDIR to control where
the output goes; the default location is /tmp/fuzzball-fuzzball-whitedisasm-output

Given the testcases generated in step 1, run them with a concrete
Bochs to collect information like their length, disassembly, and Bochs
implementation function.

The newer and faster way of doing this uses a Perl script to collect
all the instruction bytes, and runs them all through a single
execution of a program named "whitedisasm-many". The results go to the
standard output so you can name them whatever you want. For instance:

```bash
perl scripts/collect-p1-shellcode.pl /tmp/fuzzball-fuzzball-whitedisasm-output| ./tools/WhiteBochs-old/whitedisasm-many >instructions.csv
```
The older approach used shell scripts and a program
concrete-whitedisasm which ran separately for each instruction, and
stored its results in .../scripts/instructions.csv:
	cd ~/Project/pokemu-oras/scripts
	./run_analyze_shell_code.sh /tmp/fuzzball-fuzzball-whitedisasm-output/

Notes:
- Uncomment lines after "#For disasm" in scripts/commcon.py
- Don't print anything in load_fuzzball_tc (in common.py) because the output of this function is the input to concrete-whitedisasm



#### Machine State Exploring
In tools/emuFuzzBall/, run the following command:

```bash
python run-emu-fuzzball.py /home/yanxx297/Project/pokemu-oras/tools/WhiteBochs-old/fuzzball-whitebochs /home/yanxx297/Project/pokemu-oras/base.snap <shellcode> \path\to\output\dir
```

The shellcode is in the format of \\\\x__\\\\x__\\\\x__ ... where each __ is one byte or 2 letters.
Note that if the input shellcode is not in full length, the actually instruction executed by bochs will be a mixture of the given shellcode and what left in inital memory.


#### Test Case Execution
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

kvm-run/ includes code running testcases on kvm. This code interacts with kvm by api.
To run kvm-run, simply enter the emu/kvm-run directory and run the following cmd:

	./run-testcase /path/to/*.pre /output/folder

Note that the testcase is already included in the *.pre file.


### Comparing Machine State Dumps
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

### Effectiveness Experiment

## Historical Bug Experiment