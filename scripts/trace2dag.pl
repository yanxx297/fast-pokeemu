#!/usr/bin/perl

my $node;
my $last_dir;

# Describing what the branch at a given branch is doing is not so easy
# to automate, of course. Because this indexing is based on a
# particular binary, it's unfonrtunately not very reusable. This list
# is the symbolic branches encountered on exploring 0x89 0x02 on a
# particular WhiteBochs binary of SMcC's laptop
my %addr_desc =
  (
   "0x0804c65c" => "seg->cache.valid & SegAccessWOK",
   "0x08079700" => "seg->cache.valid==0",
   "0x08079714" => "seg->cache.p == 0",
   "0x0807972d" => "seg->cache.type > 5",
   "0x08079746" => "seg->cache.type <= 7",
   "0x0807974b" => "seg->cache.type > 15",
   "0x080797a9" => "seg->cache.u.segment.d_b",
   "0x080797c4" => "offset <= seg->cache.u.segment.limit_scaled",
   "0x080797cc" => "offset > upper_limit",
   "0x080797dc" => "(upper_limit - offset) < (length - 1)",
   "0x08078b48" => "(pageOffset + len) <= 4096",
   "0x0807860d" => "cr0.get_PG()",
   "0x080c4a08" => "jne in memcpy",
   "0x080c4a08_2" => "jne in memcpy 2",
   "0x080c4a08_3" => "jne in memcpy 3",
   "0x080c4a08_4" => "jne in memcpy 4",
   "0x080c4a08_5" => "jne in memcpy 5",
   "0x080c4a15" => "alignment check in memcpy",
   "0x080c4a15_2" => "alignment check in memcpy 2",
    "0x80c4a36" => "string copy in memcpy",
    "0x80c4a36_2" => "string copy in memcpy 2",
    "0x80c4a36_3" => "string copy in memcpy 3",
    "0x80c4a36_4" => "string copy in memcpy 4",
    "0x80c4a36_5" => "string copy in memcpy 5",
   "0x080786af" => "!(pde & 0x1)",
   "0x0807872e" => "pde & 0x80",
   "0x08078742" => "cr4.get_PSE()",
   "0x080788c7" => "!(pte & 0x1)",
    "0x807897a" => "priv_check[priv_index]",
   "0x0807899c" => "!(pde & 0x20)",
   "0x080789c3" => "!(pte & 0x20)",
   "0x080789d3" => "!(pte & 0x40)",
   "0x08079732" => "seg->cache.type >= 4",
   "0x0807973f" => "seg->cache.type <= 1",
   "0x0807976a" => "offset > (seg->cache.u.segment.limit_scaled - length + 1)",
   "0x0807977a" => "length-1 > seg->cache.u.segment.limit_scaled",
   "0x0807978c" => "seg->cache.u.segment.limit_scaled >= 15",
    "0x80c4a51" => "another string copy in memcpy",
  );

sub describe_node {
    my($addr) = @_;
    if (exists $addr_desc{$addr}) {
	return qq/"$addr_desc{$addr}"/;
    } else {
	return qq/"$addr"/;
    }
}

my %seen_edges;
sub maybe_edge {
    my($from, $to) = @_;
    return if $from eq "(start)";
    # die unless defined $last_dir;
    my $s = "$from $last_dir $to";
    if ($seen_edges{$s}++ == 0) {
	my $from_d = describe_node($from);
	my $to_d = describe_node($to);
	print qq/    $from_d -> $to_d [label="$last_dir"]\n/;
    }
}

my %addr_count;

print "digraph G {\n";

while (<>) {
    if (/^Symbolic branch condition \((0x.*?)\)/ or
	/^Symbolic address .* \((0x.*?)\)/) {
	my $addr = $1;
	my $count = ++$addr_count{$addr};
	my $new_node;
	if ($count == 1) {
	    $new_node = $addr;
	} else {
	    $new_node = $addr . "_$count";
	}
	maybe_edge($node, $new_node);
	$node = $new_node;
    } elsif (/^Current Path String: ([01]*)$/) {
	my $path = $1;
	$last_dir = substr($path, -1, 1);
    } elsif (/^Picked concrete value (0x[0-9a-f]+) for/) {
	my $val = $1;
	$last_dir = $1;
    } elsif (/^Iteration (\d+):/) {
	maybe_edge($node, "(end)") if $1 > 1;
	$node = "(start)";
	%addr_count = ();
    }
}
maybe_edge($node, "(end)");

print "}\n";
