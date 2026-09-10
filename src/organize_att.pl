#!/usr/bin/env perl

=head1 SCRIPT NAME

skelton.pl

=head1 DESCRIPTION

Skelton file

=cut


use lib '/data/mura/lib';
#use lib '/data21/mura/Proj/buycom/tools';
use strict;
use warnings;
use utf8;
use Encode;
use Getopt::Long;
#use cabocha;
use open 'utf8';
#use Lingua::JA::Regular::Unicode;
use TEXT::CSV_XS;

binmode STDIN, ":utf8";
binmode STDOUT, ":utf8";
binmode STDERR, ":utf8";

my ($opt_debug, $opt_h, $opt_f, $opt_dist, $opt_idx, $opt_item);
my $result = GetOptions (
    "debug" => \$opt_debug,
    "f:s" => \$opt_f,
    "item" => \$opt_item,    
    "dist" => \$opt_dist,
    "idx" => \$opt_idx,    
    "h|help" => \$opt_h
    );

if ($opt_idx) {
    &make_index;
} elsif ($opt_dist) {
    &check_distribution;
} elsif ($opt_item) {
    &main_item0818;
} else {
    #&main;
    &main2;
}

sub make_index {
    my $hash = {};

    my $csv = Text::CSV_XS->new({
	binary    => 1,
	auto_diag => 1,
	#sep_char  => "\t", # 区切り文字をタブに設定
			     });
    #my $csv = Text::CSV_XS->new();    # csvを扱う便利オブジェクト

    #gtin,attribute_canonical,attribute_raw,value,unit,value_type,record_file,variant_id,product_fact_key,evidence,source_url,grade,canonicalization_confidence
    while (my $row = $csv->getline(\*STDIN)) {
	# $row は各列が格納された配列リファレンス
	my @fields = @$row;
	
	# 例：1列目と2列目を表示する処理
	#print "Col 1: $fields[0], Col 2: $fields[1]\n";

	my $value = "";
	if ($fields[5] eq "number" && $fields[4] ne "") {
	    $value = $fields[1].":".$fields[3]."__".$fields[4];
	} else {
	    $value = $fields[1].":".$fields[3];
	}
	$hash->{$value}->{$fields[0]}++;
    }

    foreach my $attval (sort {$a cmp $b} keys %$hash) {
	my $freq = keys %{$hash->{$attval}};
	my $gtins = join ",", keys %{$hash->{$attval}};

	print "$attval\t$freq\t$gtins\n";
    }
}


sub check_distribution {
    
    my $hash = {};
    my $hash2 = {};
    my $csv = Text::CSV_XS->new({
	binary    => 1,
	auto_diag => 1,
	#sep_char  => "\t", # 区切り文字をタブに設定
			     });
    #my $csv = Text::CSV_XS->new();    # csvを扱う便利オブジェクト

    #gtin,attribute_canonical,attribute_raw,value,unit,value_type,record_file,variant_id,product_fact_key,evidence,source_url,grade,canonicalization_confidence
    while (my $row = $csv->getline(\*STDIN)) {
	# $row は各列が格納された配列リファレンス
	my @fields = @$row;

	$hash->{$fields[0]}->{$fields[1]}++;
	$hash2->{$fields[1]}->{$fields[0]}++;
    }

    foreach my $gtin (sort {$a cmp $b} keys %$hash) {
	my $freq = keys %{$hash->{$gtin}};
	my $line = join "〓", sort {$a cmp $b} keys %{$hash->{$gtin}};
	print "gtin\t$gtin\t$freq\t$line\n";
    }
    foreach my $att (sort {$a cmp $b} keys %$hash2) {
	my $freq = keys %{$hash2->{$att}};
	my $line = join "〓", sort {$a cmp $b} keys %{$hash2->{$att}};
	print "att\t$att\t$freq\t$line\n";
    }    

    
}

sub main_item0818 {
    my $hash = {};
    my $csv = Text::CSV_XS->new({
	binary    => 1,
	auto_diag => 1,
	#sep_char  => "\t", # 区切り文字をタブに設定
			     });
    #my $csv = Text::CSV_XS->new();    # csvを扱う便利オブジェクト

    #gtin,attribute_canonical,attribute_raw,value,unit,value_type,record_file,variant_id,product_fact_key,evidence,source_url,grade,canonicalization_confidence

    #0 entity_id,    1 entity_type,	2 shop_id,	3 item_id,	4 gtin,	5 variant_id,	6 attribute_canonical,	7 attribute_raw,	8 value,	9 unit,	10 value_type,	11 record_file,
    #product_fact_key,evidence,source_url,grade,canonicalization_confidence
    while (my $row = $csv->getline(\*STDIN)) {
	# $row は各列が格納された配列リファレンス
	my @fields = @$row;
	my $item = $fields[11];
	$item =~ s/\.json$//;

	
	$hash->{$item}->{raw}->{$fields[7]}++;
	$hash->{$item}->{att}->{$fields[6]}++; 
	$hash->{$item}->{gtin}->{$fields[4]}++;
	#$hash->{$item}->{freq}++;
	if ($fields[10] eq "number" && $fields[9] ne "") {
	    my $value = $fields[8]."__".$fields[9];
	    $hash->{$item}->{mem}->{$value}++;
	    $hash->{$item}->{val_gtin}->{$value}->{$fields[4]}++;
	    $hash->{$item}->{unit}->{$fields[9]}++;
	} else {
	    $hash->{$item}->{mem}->{$fields[8]}++;
	    $hash->{$item}->{val_gtin}->{$fields[8]}->{$fields[4]}++;
	    $hash->{$item}->{unit}->{text}++;
	}
    }

    print "item_id\t#GTINs\t#Att\t#UniqValues\t#Unit\tValues\tGTINs\tUnits\tValue+GTINs\tAttributes\n";
    foreach my $item (sort {$a cmp $b} keys %$hash) {
	my @tmp = ();
	foreach my $value (sort {$a cmp $b} keys %{$hash->{$item}->{val_gtin}}) {
						  
	    my @tmp_local = ();    
	    foreach my $gtin (sort {$a cmp $b} keys %{$hash->{$item}->{val_gtin}->{$value}}) {
		push @tmp_local, $gtin;
	    }
	    my $line_gtin = join ";", @tmp_local;
	    push @tmp, $value.";".$line_gtin;
	}
	my $line_valgtin = join "〓", @tmp;
	my $line = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{mem}};
	my $gtins = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{gtin}};
	my $atts = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{att}};	
	#my $freq = $hash->{$item}->{freq};
	my $freq = keys %{$hash->{$item}->{gtin}};
	my $num_value = keys %{$hash->{$item}->{mem}};
	if (exists $hash->{$item}->{unit}->{text}) {
	    my $num = keys %{$hash->{$item}->{unit}};
	    if ($num > 1) {
		delete $hash->{$item}->{unit}->{text}
	    }
	}
	my $num_unit = keys %{$hash->{$item}->{unit}};
	my $num_att = keys %{$hash->{$item}->{att}};
	my $units = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{unit}};
	
	#print "$attname\t$freq\t$variety\t$line\t$gtins\t$line_valgtin\n";
	print "$item\t$freq\t$num_att\t$num_value\t$num_unit\t$line\t$gtins\t$units\t$line_valgtin\t$atts\n";     
	
    }
}


sub main_item {
    my $hash = {};
    my $csv = Text::CSV_XS->new({
	binary    => 1,
	auto_diag => 1,
	#sep_char  => "\t", # 区切り文字をタブに設定
			     });
    #my $csv = Text::CSV_XS->new();    # csvを扱う便利オブジェクト

    #gtin,attribute_canonical,attribute_raw,value,unit,value_type,record_file,variant_id,product_fact_key,evidence,source_url,grade,canonicalization_confidence
    while (my $row = $csv->getline(\*STDIN)) {
	# $row は各列が格納された配列リファレンス
	my @fields = @$row;
	my $item = $fields[6];
	$item =~ s/\.json$//;
	# item : record_file : 6 -> 11
	# attraw : attribute_raw : 2 -> 7
	# attcal : attribute_canonical : 1 -> 6
	# gtin : gtin : 0 -> 4
	# valtype : value_type : 5 -> 10
	# unit : unit : 4 -> 9
	# value : value : 3 -> 8
	
	$hash->{$item}->{raw}->{$fields[2]}++;
	$hash->{$item}->{att}->{$fields[1]}++;	
	$hash->{$item}->{gtin}->{$fields[0]}++;
	#$hash->{$item}->{freq}++;
	if ($fields[5] eq "number" && $fields[4] ne "") {
	    my $value = $fields[3]."__".$fields[4];
	    $hash->{$item}->{mem}->{$value}++;
	    $hash->{$item}->{val_gtin}->{$value}->{$fields[0]}++;
	    $hash->{$item}->{unit}->{$fields[4]}++;
	} else {
	    $hash->{$item}->{mem}->{$fields[3]}++;
	    $hash->{$item}->{val_gtin}->{$fields[3]}->{$fields[0]}++;
	    $hash->{$item}->{unit}->{text}++;
	}
    }

    print "item_id\t#GTINs\t#Att\t#UniqValues\t#Unit\tValues\tGTINs\tUnits\tValue+GTINs\tAttributes\n";
    foreach my $item (sort {$a cmp $b} keys %$hash) {
	my @tmp = ();
	foreach my $value (sort {$a cmp $b} keys %{$hash->{$item}->{val_gtin}}) {
						  
	    my @tmp_local = ();    
	    foreach my $gtin (sort {$a cmp $b} keys %{$hash->{$item}->{val_gtin}->{$value}}) {
		push @tmp_local, $gtin;
	    }
	    my $line_gtin = join ";", @tmp_local;
	    push @tmp, $value.";".$line_gtin;
	}
	my $line_valgtin = join "〓", @tmp;
	my $line = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{mem}};
	my $gtins = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{gtin}};
	my $atts = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{att}};	
	#my $freq = $hash->{$item}->{freq};
	my $freq = keys %{$hash->{$item}->{gtin}};
	my $num_value = keys %{$hash->{$item}->{mem}};
	if (exists $hash->{$item}->{unit}->{text}) {
	    my $num = keys %{$hash->{$item}->{unit}};
	    if ($num > 1) {
		delete $hash->{$item}->{unit}->{text}
	    }
	}
	my $num_unit = keys %{$hash->{$item}->{unit}};
	my $num_att = keys %{$hash->{$item}->{att}};
	my $units = join "〓", sort {$a cmp $b} keys %{$hash->{$item}->{unit}};
	
	#print "$attname\t$freq\t$variety\t$line\t$gtins\t$line_valgtin\n";
	print "$item\t$freq\t$num_att\t$num_value\t$num_unit\t$line\t$gtins\t$units\t$line_valgtin\t$atts\n";     
	
    }
}


sub main {

    my $hash = {};
    my $csv = Text::CSV_XS->new({
	binary    => 1,
	auto_diag => 1,
	#sep_char  => "\t", # 区切り文字をタブに設定
			     });
    #my $csv = Text::CSV_XS->new();    # csvを扱う便利オブジェクト

    #gtin,attribute_canonical,attribute_raw,value,unit,value_type,record_file,variant_id,product_fact_key,evidence,source_url,grade,canonicalization_confidence
    while (my $row = $csv->getline(\*STDIN)) {
	# $row は各列が格納された配列リファレンス
	my @fields = @$row;
	
	# 例：1列目と2列目を表示する処理
	#print "Col 1: $fields[0], Col 2: $fields[1]\n";

	$hash->{$fields[1]}->{raw}->{$fields[2]}++;
	$hash->{$fields[1]}->{gtin}->{$fields[0]}++;
	$hash->{$fields[1]}->{freq}++;
	if ($fields[5] eq "number" && $fields[4] ne "") {
	    my $value = $fields[3]."__".$fields[4];
	    $hash->{$fields[1]}->{mem}->{$value}++;
	    $hash->{$fields[1]}->{val_gtin}->{$value}->{$fields[0]}++;
	    $hash->{$fields[1]}->{unit}->{$fields[4]}++;
	} else {
	    $hash->{$fields[1]}->{mem}->{$fields[3]}++;
	    $hash->{$fields[1]}->{val_gtin}->{$fields[3]}->{$fields[0]}++;
	    $hash->{$fields[1]}->{unit}->{text}++;
	}
    }

    print "attribute_canonical\t#GTINs\t#UniqValues\t#Unit\tValues\tGTINs\tUnits\tValue+GTINs\n";
    foreach my $attname (sort {$a cmp $b} keys %$hash) {
	my @tmp = ();
	foreach my $value (sort {$a cmp $b} keys %{$hash->{$attname}->{val_gtin}}) {
	    my @tmp_local = ();    
	    foreach my $gtin (sort {$a cmp $b} keys %{$hash->{$attname}->{val_gtin}->{$value}}) {
		push @tmp_local, $gtin;
	    }
	    my $line_gtin = join ";", @tmp_local;
	    push @tmp, $value.";".$line_gtin;
	}
	my $line_valgtin = join "〓", @tmp;
	my $line = join "〓", sort {$a cmp $b} keys %{$hash->{$attname}->{mem}};
	my $gtins = join "〓", sort {$a cmp $b} keys %{$hash->{$attname}->{gtin}};
	my $freq = $hash->{$attname}->{freq};
	my $num_value = keys %{$hash->{$attname}->{mem}};
	if (exists $hash->{$attname}->{unit}->{text}) {
	    my $num = keys %{$hash->{$attname}->{unit}};
	    if ($num > 1) {
		delete $hash->{$attname}->{unit}->{text}
	    }
	}
	my $num_unit = keys %{$hash->{$attname}->{unit}};
	my $units = join "〓", sort {$a cmp $b} keys %{$hash->{$attname}->{unit}};
	
	#print "$attname\t$freq\t$variety\t$line\t$gtins\n";
	#print "$attname\t$freq\t$variety\t$line\t$line_valgtin\n";
	#print "$attname\t$freq\t$variety\t$line\t$gtins\t$line_valgtin\n";
	print "$attname\t$freq\t$num_value\t$num_unit\t$line\t$gtins\t$units\t$line_valgtin\n";     
    }
}


sub main2 {

    my $hash = {};
    my $csv = Text::CSV_XS->new({
	binary    => 1,
	auto_diag => 1,
	#sep_char  => "\t", # 区切り文字をタブに設定
			     });
    #my $csv = Text::CSV_XS->new();    # csvを扱う便利オブジェクト

    #gtin,attribute_canonical,attribute_raw,value,unit,value_type,record_file,variant_id,product_fact_key,evidence,source_url,grade,canonicalization_confidence

    #0 entity_id,    1 entity_type,	2 shop_id,	3 item_id,	4 gtin,	5 variant_id,	6 attribute_canonical,	7 attribute_raw,	8 value,	9 unit,	10 value_type,	11 record_file,
    #product_fact_key,evidence,source_url,grade,canonicalization_confidence
    
    while (my $row = $csv->getline(\*STDIN)) {
	# $row は各列が格納された配列リファレンス
	my @fields = @$row;
	my $shop_item_id = $fields[11];
	$shop_item_id =~ s/\.json$//;
	#print "==> $shop_item_id\n";
	my $attname = $fields[6];
	
	# 例：1列目と2列目を表示する処理
	#print "Col 1: $fields[0], Col 2: $fields[1]\n";

	$hash->{$attname}->{raw}->{$fields[7]}++;
	$hash->{$attname}->{gtin}->{$fields[4]}++;
	$hash->{$attname}->{shop_item}->{$shop_item_id}++;
	$hash->{$attname}->{freq}++;
	if ($fields[10] eq "number" && $fields[9] ne "") {
	    foreach my $eachval (split /\|/, $fields[8]) {
		$eachval =~ s/^\s+//;
		$eachval =~ s/\s+$//;
		my $value = $eachval."__".$fields[9];
	    #my $value = $fields[8]."__".$fields[9];
		$hash->{$attname}->{mem}->{$value}++;
		$hash->{$attname}->{val_shopitem}->{$value}->{$shop_item_id}++;
		$hash->{$attname}->{unit}->{$fields[9]}++;
	    }
	} else {
	    foreach my $eachval (split /\|/, $fields[8]) {
		$eachval =~ s/^\s+//;
		$eachval =~ s/\s+$//;
		$hash->{$attname}->{mem}->{$eachval}++;
		$hash->{$attname}->{val_shopitem}->{$eachval}->{$shop_item_id}++;
		$hash->{$attname}->{unit}->{text}++;
	    }
	}
    }

    #print "$attname\t$freq\t$num_shop_item\t$num_value\t$num_unit\t$line\t$gtins\t$units\t$shop_items\t$line_valgtin\n";     
    
    print "attribute_canonical\t#GTINs\t#shopItem\t#UniqValues\t#Unit\tValues\tGTINs\tUnits\tshop_items\tValue+ShopItems\n";
    foreach my $attname (sort {$a cmp $b} keys %$hash) {
	my @tmp = ();
	foreach my $value (sort {$a cmp $b} keys %{$hash->{$attname}->{val_shopitem}}) {
	    my @tmp_local = ();    
	    foreach my $gtin (sort {$a cmp $b} keys %{$hash->{$attname}->{val_shopitem}->{$value}}) {
		push @tmp_local, $gtin;
	    }
	    my $line_gtin = join ";", @tmp_local;
	    push @tmp, $value.";".$line_gtin;
	}
	my $line_val_shopitem = join "〓", @tmp;
	my $line = join "〓", sort {$a cmp $b} keys %{$hash->{$attname}->{mem}};
	my $gtins = join "〓", sort {$a cmp $b} keys %{$hash->{$attname}->{gtin}};
	my $shop_items = join "〓", sort {$a cmp $b} keys %{$hash->{$attname}->{shop_item}};	
	my $freq = $hash->{$attname}->{freq};
	my $num_value = keys %{$hash->{$attname}->{mem}};
	my $num_shop_item = keys %{$hash->{$attname}->{mem}};	
	if (exists $hash->{$attname}->{unit}->{text}) {
	    my $num = keys %{$hash->{$attname}->{unit}};
	    if ($num > 1) {
		delete $hash->{$attname}->{unit}->{text}
	    }
	}
	my $num_unit = keys %{$hash->{$attname}->{unit}};
	my $units = join "〓", sort {$a cmp $b} keys %{$hash->{$attname}->{unit}};
	
	#print "$attname\t$freq\t$variety\t$line\t$gtins\n";
	#print "$attname\t$freq\t$variety\t$line\t$line_valgtin\n";
	#print "$attname\t$freq\t$variety\t$line\t$gtins\t$line_valgtin\n";
	print "$attname\t$freq\t$num_shop_item\t$num_value\t$num_unit\t$line\t$gtins\t$units\t$shop_items\t$line_val_shopitem\n";     
    }
}

sub _main {

    my $csv = Text::CSV_XS->new();    # csvを扱う便利オブジェクト

    open my $fp, '<', $opt_f || die "$!($opt_f)\n";
    for my $line (<$fp>) {
	chomp $line;
	my $status = $csv->parse($line); # CSV文字列をパースしてフィールド群に切り分ける
	# $status は成否判定が入っている（今回は使わない）
	my @columns = $csv->fields();    # パースされたフィールド群を配列に入れる
	print "@columns" . "\n";
    }
    close $fp;
}

