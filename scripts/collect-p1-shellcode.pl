#!/usr/bin/perl

use strict;
use IO::Zlib;

die "Usage: collect-p1-shellcode <dir>" unless @ARGV == 1;
my $dir = $ARGV[0];
die "Argument should be a directory" unless -d $dir;

opendir(DIR, $dir);
my @subdirs = readdir(DIR);
close DIR;
@subdirs = grep(/^\d{8}$/, @subdirs);
@subdirs = sort @subdirs;

my $gzfh = new IO::Zlib;

for my $sd (@subdirs) {
    #print "$sd ";
    my $tcgz = "$dir/$sd/testcase";
    die "Missing $tcgz" unless -e $tcgz;
    $gzfh->open($tcgz, "r");
    my @bytes = ();
    while (<$gzfh>) {
	chomp;
	die "Unexpected valuation <$_> in testcase"
	  unless /^in_SHELLCODE__\d+_(\d+)=0x([0-9a-f]{1,2})$/;
	my($idx, $val) = ($1, hex($2));
	$bytes[$idx] = $val;
    }
    print join("", map(sprintf("\\x%02x", $_), @bytes)), "\n";
    $gzfh->close();
}
