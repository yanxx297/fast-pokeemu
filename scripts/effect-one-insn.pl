#!/usr/bin/perl

# We use the phrase "effectiveness experiment" for experiments like
# the one in section 5.3 of the VEE'18 paper which compare the
# fault-finding performance of Fast PokeEMU to that of vanilla
# PokeEMU. This script is used to run all the parts of such an
# experiment that relate to a single instruction variant (byte
# sequence).

# This scipt takes two arguments, an output directory and an
# instruction byte sequence. For instance:

# perl effective-one-insn.pl /tmp/effect-out 013f

# It will write experimental results in the output directory and in a
# subdirectory of the output directory named after the instruction
# variant, e.g. /tmp/effect-out/ADD_EdGdM-013f.

# To run the experiment in parallel across multiple instructions, you
# may find it convenient to run under "xargs -n1 -P6", where the
# argument to -P is the number of jobs to run in parallel. For instance:

# cut -f1 data/insns | \
#   xargs -n1 -P6 perl scripts/effect-one-insn.pl /tmp/effect-out

# In addition the following environment variables are significant if
# present:

# FUZZBALL_MAX_ITERATIONS: (default 4096) maximum number of testcases
# to generate for a single instruction variant

# TIMEOUT: (default 10) maximum time, in seconds, to run one testcase

use FindBin qw($Bin);
my $pokeemu_root = "$Bin/..";
die "Can't find PokeEMU root directory"
    unless -d "$pokeemu_root/tools/emuFuzzBall";

use strict;

use File::Temp;

$| = 1;

die "Usage: effective-one-insn.pl <out-dir> <insn-bytes>"
    unless @ARGV == 2;
my($out_dir, $insn_bytes) = @ARGV;
die "Output directory $out_dir should be a writeable directory"
    unless -d $out_dir and -w $out_dir;
die "Output directory $out_dir should be an absolute path"
    unless $out_dir =~ m[^/];

$insn_bytes =~ tr/ _\\x//d;
die "Instruction bytes should be hex digits"
    unless $insn_bytes =~ /^[0-9a-fA-F]+$/;
die "Instruction bytes should be an even number of hex digits"
    if (length($insn_bytes) % 2) != 0;

my $TIMEOUT = 10;
$TIMEOUT = $ENV{"TIMEOUT"} if exists $ENV{"TIMEOUT"};

my $shellcode = $insn_bytes;
$shellcode =~ s/(..)/\\x$1/g;

my $insn_bochs;
{
    my $disasm = "$pokeemu_root/tools/WhiteBochs-old/concrete-whitedisasm";
    die "Missing $disasm; do you need to compile in " .
	"$pokeemu_root/tools/WhiteBochs-old?" unless -e $disasm;
    open(DISASM, "-|", $disasm, $shellcode)
	or die "Failed to run $disasm: $!";
    my $disasm_line = <DISASM>;
    close DISASM;
    chomp $disasm_line;
    die "Disassembly of $shellcode failed" unless length($disasm_line);
    die "Bochs says: $disasm_line" if $disasm_line =~ /prefix unallowed/;
    die "Unexpected Bochs output $disasm_line"
	unless $disasm_line =~ /^\\x.*\t.*\t.*\t.*\t.*/;
    my($d_shellcode, $d_len, $d_str, $d_opcode, $d_flags)
	= split(/\t/, $disasm_line);
    #print "$d_shellcode;$d_len;$d_str;$d_opcode;$d_flags\n";
    $shellcode = $d_shellcode;
    $insn_bytes = $shellcode;
    $insn_bytes =~ tr/ _\\x//d;
    $insn_bochs = $d_opcode;
}

my $insn_var = "$insn_bochs-$insn_bytes";
open(PROG, ">", "$out_dir/$insn_var.log")
    or die "Failed to open log file $out_dir/$insn_var.log: $!";
print "Running for $insn_var\n";
print PROG "Running for $insn_var\n";

my $subdir = "$out_dir/$insn_var";
if (-e $subdir) {
    print "Removing previous $subdir\n";
    system("/bin/rm", "-rf", $subdir);
}
die "$subdir already exists" if -e $subdir;
mkdir $subdir;

mkdir "$subdir/state-explr";
my $python = "/usr/bin/python";
die "$python is not executable" unless -x $python;
chdir "$pokeemu_root/tools/emuFuzzBall"
    or die "Failed to cd into $pokeemu_root/tools/emuFuzzBall";
die "Can't find $pokeemu_root/base.snap" unless -e "../../base.snap";
die "Can't find fuzzball-whitebochs"
    unless -e "../WhiteBochs-old/fuzzball-whitebochs";
die "Can'f find run-emu-fuzzball.py" unless -e "run-emu-fuzzball.py";
open(LOG, ">", "$subdir/state-explr.log")
    or die "Failed to open $subdir/state-explr.log for writing: $!";
open(RUN, "-|", $python, "run-emu-fuzzball.py",
     "../WhiteBochs-old/fuzzball-whitebochs", "../../base.snap",
     $shellcode, "$subdir/state-explr")
    or die "Failed to run run-emu-fuzzball.py: $!";
my($iters, $time);
while (<RUN>) {
    print LOG $_;
    if (/^Iteration (\d+):/) {
	$iters = $1;
	#print ".";
    } elsif (/^Run completed in (.*)$/) {
	$time = $1;
    }
}
#print "\n";
close RUN;
close LOG;
print "State exploration of $insn_var used $iters iteration(s), $time\n";
print PROG "State exploration of $insn_var used $iters iteration(s), $time\n";

sub run_singles
{
    my($mode, $make_agg) = @_;
    chdir "$pokeemu_root/scripts";
    opendir(SE, "$subdir/state-explr")
	or die "Failed to opendir $subdir/state-explr: $!";
    my @se_dirs = sort readdir(SE);
    close SE;
    my $qemu_script = "$pokeemu_root/emu/qemu/run-testcase";
    die "QEMU script $qemu_script does not exist" unless -e $qemu_script;
    my $kvm_script = "$pokeemu_root/emu/kvm-run/run-testcase";
    die "KVM script $kvm_script does not exist" unless -e $kvm_script;
    my $tc_out_dir = File::Temp->newdir(CLEANUP => 0);
    my $temp_dir = File::Temp->newdir();
    open(LOG, ">", "$subdir/single-m$mode.log")
	or die "Failed to open $subdir/single-m$mode.log for writing: $!";
    open(MATCHES, ">", "$tc_out_dir/match")
	or die "Failed to poen $tc_out_dir/match for writing: $!";
    open(MISMATCHES, ">", "$tc_out_dir/mismatch")
	or die "Failed to poen $tc_out_dir/mismatch for writing: $!";
    my($match_cnt, $mismatch_cnt, $fail_cnt) = (0, 0, 0);
    my @usable_tcs = ();
    for my $se_dir (@se_dirs) {
	next unless $se_dir =~ /^\d{8}$/;
	die "$subdir/state-explr/$se_dir should be a directory"
	    unless -d "$subdir/state-explr/$se_dir";
	my $testcase = "$subdir/state-explr/$se_dir/testcase";
	die "$testcase should exist" unless -e $testcase;
	my @tc_args;
	push @tc_args, "testcase:$testcase";
	push @tc_args, "timeout:$TIMEOUT";
	push @tc_args, "outdir:$tc_out_dir";
	push @tc_args, "script:$qemu_script";
	push @tc_args, "mode:$mode";
	push @tc_args, "tmp:$temp_dir";
	push @tc_args, "loop:1";
	open(RUN, "-|", $python, "run_test_case.py", @tc_args)
	    or die "Failed to run run_test_case.py: $!";
	while (<RUN>) {
	    print LOG $_;
	}
	close RUN;
	#print "q";
	my $prestate = "$tc_out_dir/$se_dir.pre";
	my $qemu_poststate = "$tc_out_dir/$se_dir.post";
	if (not -e $prestate) {
	    $fail_cnt++;
	    next;
	}
	my $kvm_poststate = "$tc_out_dir/$se_dir.kvm.post";
	open(RUN, "-|", "/usr/bin/timeout", $TIMEOUT,
	     $kvm_script, $prestate, $kvm_poststate)
	    or die "Failed to run $kvm_script: $!";
	while (<RUN>) {
	    print LOG $_;
	}
	close RUN;
	#print "k";
	my $diff_file = "$tc_out_dir/$se_dir.diff";
	open(DIFF, ">", $diff_file)
	    or die "Failed to open $diff_file for writing: $!";
	open(RUN, "-|", $python, "diff_cpustate.py",
	     $qemu_poststate, $kvm_poststate);
	while (<RUN>) {
	    print DIFF $_;
	}
	close RUN;
	my $diff_status = ($? >> 8);
	close DIFF;
	if ($diff_status == 0) {
	    #print "Match.\n";
	    print MATCHES "$se_dir\n";
	    $match_cnt++;
	    push @usable_tcs, $testcase;
	} elsif ($diff_status == 2) {
	    #print "Mismatch.\n";
	    print MISMATCHES "$se_dir\n";
	    $mismatch_cnt++;
	    push @usable_tcs, $testcase;
	} elsif ($diff_status == 1) {
	    #print "Failure.\n";
	    $fail_cnt++;
	} else {
	    die "Unexpected diff status $diff_status.\n";
	}
    }
    close LOG;
    close MATCHES;
    close MISMATCHES;
    #print "\n";
    system("/bin/mv", $tc_out_dir, "$subdir/single-m$mode");
    print "$insn_var s$mode has $match_cnt match, $mismatch_cnt mismatch, ".
	"$fail_cnt failures\n";
    print PROG "$insn_var s$mode has $match_cnt match, $mismatch_cnt mismatch, "
	."$fail_cnt failures\n";
    my $stat = $mismatch_cnt > 0 ? 1 : 0;
    if ($make_agg) {
	return ($stat, 0) if not @usable_tcs;
	open(LIST, ">", "$subdir/aggreg.list")
	    or die "Failed to open $subdir/aggreg.list for writing: $!";
	print LIST join(",", @usable_tcs);
	close LIST;
	system($python, "$pokeemu_root/scripts/split_log.py",
	       "$subdir/aggreg.list", 600);
	return ($stat, 1);
    }
    return $stat;
}

my($s3_stat, $viable) = run_singles(3, 1);
my $s0_stat = run_singles(0);
# run_singles(1);
# run_singles(2);

sub run_aggregs
{
    my($mode) = @_;
    chdir "$pokeemu_root/scripts";
    opendir(SD, "$subdir") or die "Failed to opendir $subdir: $!";
    my @groups = sort grep(/^\d+\.log/, readdir(SD));
    close SD;
    my $qemu_script = "$pokeemu_root/emu/qemu/run-testcase";
    die "QEMU script $qemu_script does not exist" unless -e $qemu_script;
    my $kvm_script = "$pokeemu_root/emu/kvm-run/run-testcase";
    die "KVM script $kvm_script does not exist" unless -e $kvm_script;
    my $tc_out_dir = File::Temp->newdir(CLEANUP => 0);
    my $temp_dir = File::Temp->newdir();
    open(LOG, ">", "$subdir/aggreg-m$mode.log")
	or die "Failed to open $subdir/aggreg-m$mode.log for writing: $!";
    open(MATCHES, ">", "$tc_out_dir/match")
	or die "Failed to poen $tc_out_dir/match for writing: $!";
    open(MISMATCHES, ">", "$tc_out_dir/mismatch")
	or die "Failed to poen $tc_out_dir/mismatch for writing: $!";
    my($match_cnt, $mismatch_cnt, $fail_cnt) = (0, 0, 0);
    for my $group (@groups) {
	die unless $group =~ /^(\d+)\.log/;
	open(GROUP, "<", "$subdir/$group")
	    or die "Failed to open $subdir/$group: $!";
	my $testcases = <GROUP>;
	chomp $testcases;
	close GROUP;
	die unless $testcases =~ m[/(\d{8})/testcase$];
	my $group_num = $1;
	my @tc_args;
	push @tc_args, "testcase:$testcases";
	push @tc_args, "timeout:$TIMEOUT";
	push @tc_args, "outdir:$tc_out_dir";
	push @tc_args, "script:$qemu_script";
	push @tc_args, "mode:$mode";
	push @tc_args, "tmp:$temp_dir";
	push @tc_args, "loop:1";
	open(RUN, "-|", $python, "run_test_case.py", @tc_args)
	    or die "Failed to run run_test_case.py: $!";
	while (<RUN>) {
	    print LOG $_;
	}
	close RUN;
	#print "q";
	my $prestate = "$tc_out_dir/$group_num.pre";
	my $qemu_poststate = "$tc_out_dir/$group_num.post";
	if (not -e $prestate) {
	    $fail_cnt++;
	    next;
	}
	my $kvm_poststate = "$tc_out_dir/$group_num.kvm.post";
	open(RUN, "-|", "/usr/bin/timeout", $TIMEOUT,
	     $kvm_script, $prestate, $kvm_poststate)
	    or die "Failed to run $kvm_script: $!";
	while (<RUN>) {
	    print LOG $_;
	}
	close RUN;
	#print "k";
	my $diff_file = "$tc_out_dir/$group_num.diff";
	open(DIFF, ">", $diff_file)
	    or die "Failed to open $diff_file for writing: $!";
	open(RUN, "-|", $python, "diff_cpustate.py",
	     $qemu_poststate, $kvm_poststate);
	while (<RUN>) {
	    print DIFF $_;
	}
	close RUN;
	my $diff_status = ($? >> 8);
	close DIFF;
	if ($diff_status == 0) {
	    print MATCHES "$group_num\n";
	    $match_cnt++;
	} elsif ($diff_status == 2) {
	    print MISMATCHES "$group_num\n";
	    $mismatch_cnt++;
	} elsif ($diff_status == 1) {
	    $fail_cnt++;
	} else {
	    die "Unexpected diff status $diff_status.\n";
	}
    }
    close LOG;
    close MATCHES;
    close MISMATCHES;
    #print "\n";
    system("/bin/mv", $tc_out_dir, "$subdir/aggreg-m$mode");
    print "$insn_var a$mode has $match_cnt match, $mismatch_cnt mismatch, ".
	"$fail_cnt failures\n";
    print PROG "$insn_var a$mode has $match_cnt match, $mismatch_cnt mismatch, "
	."$fail_cnt failures\n";
    return $mismatch_cnt > 0 ? 1 : 0;
}

if ($viable) {
    my $m3_stat = run_aggregs(3);

    my $class = $s0_stat . $s3_stat . $m3_stat;

    print "$class $insn_var\n";
    print PROG "$class $insn_var\n";

    open(CLASS, ">>", "$out_dir/$class")
      or die "Failed to open $out_dir/$class to append: $!";
    print CLASS "$insn_var\n";
    close CLASS;
} else {
    print "unviable $insn_var\n";
    print PROG "unviable $insn_var\n";
}

system("/bin/rm", "-rf", "$subdir/state-explr");
system("/bin/rm", "-rf", "$subdir/single-m0");
system("/bin/rm", "-rf", "$subdir/single-m3");
system("/bin/rm", "-rf", "$subdir/aggreg-m3");
system("/usr/bin/xz", "$subdir/state-explr.log");
system("/usr/bin/xz", "$subdir/single-m0.log");
system("/usr/bin/xz", "$subdir/single-m3.log");
system("/usr/bin/xz", "$subdir/aggreg-m3.log");

close PROG;
