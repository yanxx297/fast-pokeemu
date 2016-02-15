#!/usr/bin/perl

use strict;

my @seqs = @ARGV;

mkdir("/tmp/regen") unless -d "/tmp/regen";

foreach my $s (@seqs) {
    opendir(DIR, "/tmp/$s") or die "/tmp/$s: $!";
    mkdir("/tmp/regen/$s") unless -d "regen$s";
    foreach my $n (sort readdir(DIR)) {
	next unless $n =~ /^[0-9]{8}$/;
	die unless $n =~ /^0000([0-9]{4})$/;
	my $short_n = $1;
	print STDERR "$short_n: ";
	my $outdir = "/tmp/regen/$s/$short_n";
	mkdir($outdir) unless -d $outdir;
	my $tc = "/tmp/$s/$n/testcase";
	my $kern = "/tmp/kernel-$s-$short_n";
	my $floppy = "/tmp/floppy-$s-$short_n";
	system("/home/yanxx297/Project/pokemu-oras/scripts/print_test_case.py $tc >$outdir/ptc.txt");
	system("/home/yanxx297/Project/pokemu-oras/scripts/gen_floppy_image.py debug:2 testcase:$tc kernel:$kern floppy:$floppy >$outdir/gen.log");
	open(DIS, ">", "$outdir/test.dis");
	open(OBJDUMP, "objdump -d -j .testcase $kern |");
	while (<OBJDUMP>) {
	    print DIS $_ if /<testcase>/ .. /\tf4\s+\thlt/;
	}
	close OBJDUMP;
	close DIS;
	system("xdelta3 -f -s kernel-base $kern $outdir/kernel.vcd");
	system("xdelta3 -f -s floppy-base $floppy $outdir/floppy.vcd");
	unlink($kern);
	unlink($floppy);
    }
}
