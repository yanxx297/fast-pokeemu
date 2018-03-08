#!/usr/bin/perl

use strict;

my $header_size = 1523;
my $mem_size = 4 * 2**20; # 4MB

die "Usage: compare-mem.pl base.snap test.post" unless @ARGV == 2;

my($base_fname, $test_fname) = @ARGV;
my($base_mem, $test_mem);

die "$base_fname does not exist" unless -e $base_fname;
open(BASE, "<$base_fname") or die "Failed to open $base_fname: $!";
read(BASE, my($buf), 4);
if ($buf eq "\xef\xef\x01\x00") {
    #print STDERR "$base_fname is an uncompressed snapshot\n";
    seek(BASE, 0, 0);
} elsif (substr($buf, 0, 2) eq "\x1f\x8b") {
    #print STDERR "$base_fname is gzip compressed\n";
    close BASE;
    open(BASE, "zcat $base_fname |") or die "Failed to zcat $base_fname: $!";
} else {
    die "$base_fname has an unrecognized format";
}
read(BASE, $buf, $header_size); # skip 1523-byte header
read(BASE, $base_mem, $mem_size);
die "Short read of $base_fname memory area"
  unless length($base_mem) == $mem_size;
close BASE;

die "$test_fname does not exist" unless -e $test_fname;
open(TEST, "<$test_fname") or die "Failed to open $test_fname: $!";
read(TEST, my($buf), 4);
if ($buf eq "\xef\xef\x01\x00") {
    #print STDERR "$test_fname is an uncompressed snapshot\n";
    seek(TEST, 0, 0);
} elsif (substr($buf, 0, 2) eq "\x1f\x8b") {
    #print STDERR "$test_fname is gzip compressed\n";
    close TEST;
    open(TEST, "zcat $test_fname |") or die "Failed to zcat $test_fname: $!";
} else {
    die "$test_fname has an unrecognized format";
}
read(TEST, $buf, $header_size); # skip 1523-byte header
read(TEST, $test_mem, $mem_size);
die "Short read of $test_fname memory area"
  unless length($test_mem) == $mem_size;
close TEST;

my $base_diff_count = 0;
my $tcase_diff_count = 0;
my $data_diff_count = 0;

for (my $i = 0; $i < $mem_size; $i += 16) {
    my $chunk = substr($test_mem, $i, 16);
    if ($chunk eq "\0" x 16 or $chunk eq "\x90" x 16 or
	$chunk eq "\xf4" x 16 or $chunk eq "\xff" x 16) {
	# Count strings of 0 bits, 1 bits, NOPs (\x90) or HALTs (\xf4)
	# as empty
	next;
    }
    my $base_chunk = substr($base_mem, $i, 16);
    for (my $j = 0; $j < 16; $j++) {
	my $addr = $i + $j;
	if (substr($base_chunk, $j, 1) ne substr($chunk, $j, 1)) {
	    #printf "0x%06x: %02x vs. %02x\n", $addr,
	    #  ord(substr($base_chunk, $j, 1)), ord(substr($chunk, $j, 1));
	    if ($addr < 0x219000) {
		$base_diff_count++;
	    } elsif ($addr < 0x28d000) {
		$tcase_diff_count++;
	    } else {
		$data_diff_count++;
	    }
	}
    }
}

#printf "%d bytes differ (%.1f KB, %.1f%%)\n", $diff_count, $diff_count/1024,
#  100*($diff_count/$mem_size);

print "$tcase_diff_count $data_diff_count $base_diff_count\n";

