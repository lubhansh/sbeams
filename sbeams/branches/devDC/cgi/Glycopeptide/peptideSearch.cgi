#!/usr/local/bin/perl

###############################################################################
# $Id$
#
# SBEAMS is Copyright (C) 2000-2005 Institute for Systems Biology
# This program is governed by the terms of the GNU General Public License (GPL)
# version 2 as published by the Free Software Foundation.  It is provided
# WITHOUT ANY WARRANTY.  See the full description of GPL terms in the
# LICENSE file distributed with this software.
###############################################################################


###############################################################################
# Get the script set up with everything it will need
###############################################################################
use strict;
use vars qw ($q $sbeams $sbeamsMOD $PROG_NAME
             $current_contact_id $current_username $glyco_query_o);
use lib qw (../../lib/perl);
use CGI::Carp qw(fatalsToBrowser croak);
use Data::Dumper;

use SBEAMS::Connection qw($q $log);
use SBEAMS::Connection::Settings;
use SBEAMS::Connection::Tables;
use SBEAMS::Connection::TabMenu;

use SBEAMS::BioLink::KeggMaps;

use SBEAMS::Glycopeptide;
use SBEAMS::Glycopeptide::Settings;
use SBEAMS::Glycopeptide::Tables;

use SBEAMS::Glycopeptide::Get_glyco_seqs;
use SBEAMS::Glycopeptide::Glyco_query;


$sbeams = new SBEAMS::Connection;
$sbeamsMOD = new SBEAMS::Glycopeptide;
$sbeamsMOD->setSBEAMS($sbeams);

$glyco_query_o = new SBEAMS::Glycopeptide::Glyco_query;
$glyco_query_o->setSBEAMS($sbeams);

my $keggmap = SBEAMS::BioLink::KeggMaps->new();

###############################################################################
# Global Variables
###############################################################################
$PROG_NAME = 'main.cgi';
my $file_name    = $$ . "_glyco_predict.png";
my $tmp_img_path = "images/tmp";
my $img_file     = "$PHYSICAL_BASE_DIR/$tmp_img_path/$file_name";

my $predicted_track_type = "Predicted Peptides";
my $id_track_type 		 = 'Observed Peptides';
my $glyco_site_track = "N-Glyco Sites";
$sbeams->setSBEAMS_SUBDIR($SBEAMS_SUBDIR);
my $base_url = "$CGI_BASE_DIR/$SBEAMS_SUBDIR/peptideSearch.cgi";

my %search_types = ( gene_symbol => 'Gene Symbol',
                     gene_name   => 'Protein Name/Alias',
                     swiss_prot  => 'SwissProt Accession Number',
                     accession   => 'Accession (ID)',
                     gene_id     => 'Entrez GeneID'
                   );

my @search_types = qw( accession gene_name swiss_prot gene_symbol gene_id );

my $motif_type;

main();


###############################################################################
# Main Program:
#
# Call $sbeams->Authentication and stop immediately if authentication
# fails else continue.
###############################################################################
sub main 
{ 
    #### Do the SBEAMS authentication and exit if a username is not returned
    exit unless ($current_username = $sbeams->Authenticate(
        #permitted_work_groups_ref=>['Glycopeptide_user','Glycopeptide_admin', 'Glycopeptide_readonly'],
        # connect_read_only=>1,
        allow_anonymous_access=>1,
    ));

#    for my $p ( $q->param() ) { $log->info( "$p => " . $q->param( $p ) ); }

    #### Read in the default input parameters
    my %parameters;
    my $n_params_found = $sbeams->parse_input_parameters(
        q=>$q,
        parameters_ref=>\%parameters
        );
    if ( $parameters{unipep_build_id} ) {
      my $build_id = $sbeamsMOD->get_current_build( build_id => $parameters{unipep_build_id} );
      if ( $build_id != $parameters{unipep_build_id} ) {
        $sbeams->set_page_message( type => 'Error', msg => 'You must log in to access specified build' );
      }
    }
    $motif_type = $sbeamsMOD->get_current_motif_type();

    ## get project_id to send to HTMLPrinter display
    my $project_id = $sbeams->getCurrent_project_id();

    #### Process generic "state" parameters before we start
    $sbeams->processStandardParameters(parameters_ref=>\%parameters);
    #$sbeams->printDebuggingInfo($q);

    #### Decide what action to take based on information so far
    $sbeamsMOD->display_page_header(project_id => $project_id);
#    $sbeams->printStyleSheet();
    if ($parameters{action} eq "Show_detail_form" || $parameters{redraw_protein_sequence} == 1) {
		
		 clean_params(\%parameters);
		
		 my $ipi_data_id = $parameters{'ipi_data_id'};
		
    print $sbeams->getGifSpacer(800);
		print $sbeams->getPopupDHTML();
    display_detail_form( ref_parameters => \%parameters,
                            ipi_data_id => $ipi_data_id  );
		
	}elsif($parameters{action} eq 'Show_hits_form'){
		
#		 $sbeamsMOD->display_page_header(project_id => $project_id);
    print $sbeams->getGifSpacer(800);
		print $sbeams->getPopupDHTML();
		
		display_hits_form(ref_parameters=>\%parameters);
#		$sbeamsMOD->display_page_footer();
    
    } else {

#        $sbeamsMOD->display_page_header(project_id => $project_id);
    print $sbeams->getGifSpacer(800);
		handle_request(ref_parameters=>\%parameters);
#		$sbeamsMOD->display_page_footer();

    }

		$sbeamsMOD->display_page_footer(close_tables=>'NO');



} # end main

###############################################################################
# Show the main welcome page
###############################################################################
sub handle_request {
 	my %args = @_;

  #### Process the arguments list
 	my $ref_parameters = $args{'ref_parameters'} || die "ref_parameters not passed";

 	my %parameters = %{$ref_parameters};
  my $motif = $sbeamsMOD->get_current_motif_type();
  my $title = '';
  my $intro = '';
  my %example;

  my $organism = $sbeamsMOD->get_current_organism();

  if ( $motif !~ /phospho/ ) {
    $title = "ISB N-glycosylation peptide prediction server";
    $intro =<<"    END";
    "The ISB N-Glyco prediction server shows all the N-linked glycosylation site contained 
    within predicted and identified tryptic peptides.  
    The Glyco score indicates how likely the site is glycosylated and the detection score
    is an indication on how likely the glycosylated peptide will be detected in a MS/MS run.  This is 
    useful for quantitating proteins of interest. 
    <br>
    Click <a href='http://www.ncbi.nlm.nih.gov/entrez/query.fcgi?cmd=Retrieve&db=pubmed&dopt=Abstract&list_uids=15637048'>here</a>
    for more information."
    END

    %example = ( name =>'jaguar',
                 sym => 'jar',
                 seq => '%ESNGQVEDSPPVIRNGVNDASPMGPNKLISFSQVVSNIASRYLNKSENVRAQQQALGKQK%',
                 acc => 'FBgn0011225' );

  } else {
    $title = "ETH/ISB Phosphosite server";
    $intro =<<"    END";
    Database of observed phosphorylation sites
    END

    $log->debug( "org is $organism");
    if ( $organism eq 'Drosophila' ) {
      %example = ( name =>'jaguar',
                   symbol => 'jar',
                   seq => '%ESNGQVEDSPPVIRNGVNDASPMGPNKLISFSQVVSNIASRYLNKSENVRAQQQALGKQK%',
                   esc_seq => '%25ESNGQVEDSPPVIRNGVNDASPMGPNKLISFSQVVSNIASRYLNKSENVRAQQQALGKQK%25',
                   acc => 'FBgn0011225' );
    } elsif (  $organism eq 'Yeast' ) {
      %example = ( name =>'S000000920',
                   synonym => 'SHO1',
                   symbol => 'SHO1',
                   seq => '%WIDSFSIKGIRPSPLENSLHRAR%',
                   esc_seq => '%25WIDSFSIKGIRPSPLENSLHRAR%25',
                   acc => 'YER118C' );
    } elsif (  $organism eq 'C Elegans' ) {
      %example = ( name =>'Vitellogenin',
                   synonym => 'AAA98720.1',
                   symbol => 'CE06950',
                   seq => '%HQLTEASGSVCK',
                   esc_seq => '%25HQLTEASGSVCK%25',
                   acc => 'C42D8.2a' );
    } elsif (  $organism eq 'Human' ) {
      %example = ( name =>'Insulin receptor substrate-2',
                   synonym => 'Insulin receptor substrate-2 (IRS-2).',
                   symbol => 'IRS2',
                   seq => '%CSHRSNTPESIAETPPARDG%',
                   esc_seq =>  '%25CSHRSNTPESIAETPPARDG%25',
                   acc => 'IPI00000782' );
    } else {
      %example = ( name =>'flutflut',
                   symbol => 'flut',
                   seq => '%ESNGQVEDSPPVIRNGVNDASPMGPNKLISFSQVVSNIASRYLNKSENVRAQQQALGKQK%',
                   esc_seq => '%25ESNGQVEDSPPVIRNGVNDASPMGPNKLISFSQVVSNIASRYLNKSENVRAQQQALGKQK%25',
                   acc => 'GOD_1' );
    }
  }
	
	print 
	$q->table({class=>'table_setup'},
          $q->Tr({class=>'rev_gray_head'},
	     $q->td({colspan=>2, class=>'rev_gray_head'}, $title ),
	  	 
	  ),
	  $q->Tr(
 	     $q->td({colspan=>2}, $intro
	     )
	 ), 
	$q->Tr(
	   $q->td({colspan=>2},'&nbsp; <br> &nbsp;') 
	 ),	    
	 $q->Tr({class=>'rev_gray_head'},
	   $q->td({colspan=>2, class=>'rev_gray_head'}, "Text Search")
	 ),
	 $q->Tr(
	   $q->td({class=>'grey_bg'}, "Choose Search option"),
	   $q->td(
	      $q->start_form(),
	      $q->popup_menu( -name=>'search_type',
                        -values=> [ @search_types ],
                        -labels => \%search_types,
                        -default=>['Accession'],
                        -size=>1,      
	   			)
	   )
	 ),
	 $q->Tr(
	  $q->td({class=>'grey_bg'},'Search Term'),
	  $q->td(
	     $q->textfield(-name=>'search_term',
                           -value=>'',
                           -size=>50,
                           -maxlength=>80)
	  )  
	 ),
	 $q->Tr(
 	   $q->td({class=>'blue_bg_glyco', colspan=>2}, "Wildcard character '%' can be used to broaden the search")
	 ),
	
	 $q->Tr(
	   $q->td({colspan=>2}, " <B>-- or --</B> <br>")
	 ), 
	 $q->Tr({class=>'rev_gray_head'},
	   $q->td({colspan=>2, class=>'rev_gray_head'}, "Sequence Search" )
	 ), 
	 
	 $q->Tr(
	    $q->td({class=>'grey_bg'}, "Search by Protein Sequence"),
	    $q->td(
	       $q->textarea(-name=>'sequence_search',
                          -default=>'',
                          -rows=>8,
                          -columns=>50)
	    )
	 ),
	 $q->Tr(
	    $q->td({class=>'blue_bg_glyco', colspan=>2}, "Sequence search wildcard is also '%', sequences will be truncated at 500 residues.")
	 ),
	

	),#end table
	
	$q->submit(), 
	$q->reset(),
	$q->hidden(-name=>'action',
               -default=>['Show_hits_form']),
	$q->endform();

### add an Example table
	my $cgi_url = "$base_url?action=Show_hits_form&search_type";
	my $seq_url = "$base_url?action=Show_hits_form;sequence_search";
  my $gene_id_row = '';
  $gene_id_row = $q->Tr( $q->td({class=>'grey_bg'}, "Gene ID"),
                         $q->td($q->a({href=>"$cgi_url=GeneID&search_term=214"}, "214") )
	                      ) if $example{gene_id};
	print 
	"<br><br>",
	$q->table(
	   $q->Tr(
	      $q->td({class=>'rev_gray_head', colspan=>2}, "Examples")
	   ),
	   $q->Tr(
              $q->td({class=>'grey_bg'}, "Gene Symbol"),
              $q->td($q->a({href=>"$cgi_url=gene_symbol&search_term=$example{symbol}"}, $example{symbol}) )
	   ),
	   $q->Tr(
              $q->td({class=>'grey_bg'}, "Protein Name/Alias"),
              $q->td($q->a({href=>"$cgi_url=gene_name&search_term=$example{name}"}, "$example{name}") )
	   ),
	   $q->Tr(
              $q->td({class=>'grey_bg'}, "Accession (ID)"),
              $q->td($q->a({href=>"$cgi_url=accession&search_term=$example{acc}"}, "$example{acc}") )
	   ),
	   $q->Tr(
              $q->td({class=>'grey_bg'}, "Protein Sequence"),
              $q->td($q->a({href=>"$seq_url=$example{esc_seq}"}, "$example{seq}") )

	   ),
     $gene_id_row
	);
}
###############################################################################
# Show hits form
###############################################################################
sub display_hits_form {
 	my %args = @_;


  #### Process the arguments list
  my $params = $args{'ref_parameters'} || die "ref_parameters not passed";
  my $sql_data = find_hits($params);

}

###############################################################################
#find_hits
#Check the parameter and figure out what query to run
###############################################################################
sub find_hits{

	my $ref_parameters = shift;
				  
	#check to see if this is a sequence or text search
	my $type = check_search_params( $ref_parameters );
	my $resultset = [];
	
  if ($type eq 'text'){
    $resultset = $glyco_query_o->keyword_search( %$ref_parameters );	
  }elsif($type eq 'sequence_search'){
    $resultset = $glyco_query_o->protein_seq_query( $ref_parameters->{sequence_search} );	
  }else{
    print_error("Cannot find correct search type to run '$type'");
  }
	
	
	
  if ( $resultset ){
    	
    if ( scalar(@$resultset) == 1 ) {
      #pull out the ipi_id and directly display the details page since there is only one hit
      my $href_results_info = $resultset->[0];
      my $ipi_data_id = $href_results_info->{'ipi_data_id'};
      display_detail_form( ipi_data_id 	=> $ipi_data_id, 
                         ref_parameters	=> $ref_parameters );
		} else {
      my $motif_type = $sbeamsMOD->get_current_motif_type();
      if ( $motif_type eq 'phospho' ) {
        print_out_phospho_hits_page(results_set_aref => $resultset,
					                           ref_parameters  => $ref_parameters);
      } else {
        print_out_hits_page(results_set_aref => $resultset,
			  		                 ref_parameters  => $ref_parameters);
      }
    }

  }else{
    my $term = $ref_parameters->{search_term} || $ref_parameters->{sequence_search};
    print $q->h3( "No hits were found with the query '$term'" );
  }

}

###############################################################################
#print_out_hits_page
#
###############################################################################
sub print_out_hits_page{
	
	my %args = @_;

	my @results_set = @{ $args{results_set_aref} };
	my %parameters = %{ $args{ref_parameters} };
  my $html;

	if (exists $parameters{similarity_score} && defined $parameters{similarity_score}){
		$html .= $q->p(
			$q->h3("Protein Similarity Score (Percent Match) <span class='lite_blue_bg'>" . $parameters{similarity_score} . "</span>"),
		);
	}
	
	$html .= $q->start_table();
  $html .= $q->Tr({class=>'rev_gray_head'},
			  $q->td('ID'),
			  $q->td('Protein Name'),
			  $q->td('Protein Symbol'),
			  $q->td('Identified Peptides')
			);
  $log->info( $html );
	my $cgi_url = "$base_url?action=Show_detail_form&ipi_data_id";
  my $protcnt = 0;
  my $pepprotcnt = 0;
  my $cutoff = $sbeamsMOD->get_current_prophet_cutoff();
  my $pepcnt = 0;
  my @symbols;
	foreach my $h_ref (@results_set){
		my $ipi_id = $h_ref->{ipi_data_id};
		my $num_identified = $h_ref->{num_observed};
		my $ipi_acc = $h_ref->{ipi_accession_number};
		my $protein_name = nice_term_print($h_ref->{protein_name});
		my $protein_sym = $h_ref->{protein_symbol};
    push @symbols, $protein_sym if $protein_sym;
    $protcnt++;
    $pepprotcnt++ if $num_identified;
    $pepcnt += $num_identified;
		$html .= join( "\n", $q->Tr(
			    $q->td(
			    	$q->a({href=>"$cgi_url=$ipi_id"},$ipi_acc)
			    ),
			    $q->td($protein_name),
			    $q->td($protein_sym),
			    $q->td({ALIGN=>'right'},$num_identified)
          )
        );
	}
	$html .= "</table>";

  my $organism = 'human';
  my $gXML = $sbeams->getGaggleXML( object => 'namelist', 
                                      type => 'direct',
                                      name => "Gene symbols",
                                      data => \@symbols,
                                     start => 1, 
                                       end => 1,
                                     organism => $organism );
  $html .= "\n$gXML\n";

  my $type = ( check_search_params(\%parameters) eq 'text' ) ? 
                                                      $parameters{search_type} :
                                                       'sequence';
  my $value = '';
  if ($type eq 'sequence') {
    $value = $parameters{sequence_search};
    if ( length($value) > 12 ) {
      $value = substr($value, 0, 12) . '...';
    }
  } else {
    $value = $parameters{search_term};
  }

  my $ofwhich = "of which $pepprotcnt";
  my $contain = ( $pepprotcnt > 1 ) ? 'contain' : 'contains';
  if ( $pepprotcnt == $protcnt || $pepcnt == 0 ) {
    $ofwhich = 'which';
  }

  my $stats = qq~
  <BR><FONT COLOR=GREEN>
  Your search for proteins with $type = 
  '$value'  found  $protcnt proteins $ofwhich $contain
  a total of $pepcnt peptides at a prophet cutoff of $cutoff
  </FONT>
  <BR>
  <BR>
  ~;
  print "$stats $html";
}

###############################################################################
#nice_term_print
#put breaks into long lines
###############################################################################
sub nice_term_print{
	my $info = shift;
	my @html = ();
	
	my $info = substr($info, 0, 75, '...'); #chop things down to 75 or less
	my @hold = split /\s/, $info;
	
	my $count = 0;
	foreach my $term(@hold){
		if ($count <= 5){
			push @html, $term;
		}else{
			$count == 0;
			push @html, "$term<br>";
		}
	
	}
	return join " ", @html;
}

###############################################################################
#print_error
#print a simple error message
###############################################################################
sub print_error{
	my $error = shift;
	
	print $q->header,
	$q->start_html,
	$q->p($q->h3($error)),
	$q->end_html;
	
	exit;
	
}

###############################################################################
#check_search_params
#Make sure that the params only have a text search or sequence not both
###############################################################################
sub check_search_params{
	my $ref_parameters = shift;
	
	if ($ref_parameters->{search_term} =~ /\w/){
		if ($ref_parameters->{sequence_search} =~ /\w/ ){
			print_error("Cannot have a Text Search and Sequence Search in the same query");
		}
	}elsif($ref_parameters->{sequence_search} =~ /\w/ ) {
		return ('sequence_search');
	}
	return 'text';

}

###############################################################################
#clean_params
#foreach param this script knows about make sure nothing bad is comming in from the outside
###############################################################################
sub clean_params{
	my $ref_parameters = shift;
	
	KEY:foreach my $k (keys %{$ref_parameters}){

		if ($k eq 'action'){
			$ref_parameters->{$k} = clean_action($ref_parameters->{$k});
		}elsif($k eq 'search_type' ){
		
			next KEY if ( $ref_parameters->{'sequence_search'} );# ignore if this is a sequnce search
			
			($ref_parameters->{$k},$ref_parameters->{'search_term'} ) = 
				check_search_term(type=>$ref_parameters->{$k},
							      term =>$ref_parameters->{'search_term'});
			
		
		}elsif($k eq 'search_term'){
		 	next; #already scaned above
		
		}elsif($k eq 'sequence_search'){
			$ref_parameters->{$k} = clean_seq($ref_parameters->{$k});
		}elsif($k eq 'ipi_data_id'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}elsif($k eq 'similarity_score'){
			 $ref_parameters->{$k} = clean_term($ref_parameters->{$k});
##Parameters for re-drawing the protien map
		}elsif($k eq 'Glyco Site'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}elsif($k eq 'Predicted Peptide'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}elsif($k eq 'Identified Peptide'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}elsif($k eq 'Signal Sequence'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}elsif($k eq 'Trans Membrane Seq'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}elsif($k eq 'redraw_protein_sequence'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}elsif($k eq 'autorun'){
			$ref_parameters->{$k} = clean_term($ref_parameters->{$k});
		}else{
# Doesn't allow std sbeams params through
#print_error("Unknown Paramater passed in '$k' ")
		}	
   
	}
	return $ref_parameters;
}
###############################################################################
#clean_seq
#Clean the sequence to a single clean AA string, but allow wild cards to pass
###############################################################################
sub clean_seq{
	my $seq = shift;
	
  # Does this work on winders?
  my @seq_lines = split/\n/, $seq;
  chomp @seq_lines;

	my @clean_seq = ();
	
	foreach my $line (@seq_lines){
		next if( $line =~ /^>/);
		$line =~ s/[^A-Z\%]//g;
		push @clean_seq, $line
	}
	my $seq_line = join '', @clean_seq;
	$seq_line = substr($seq_line, 0, 500);
	return $seq_line;
}


###############################################################################
#check_search_term
#Make sure the search term is appropriate for the search type
###############################################################################
sub check_search_term{
	my %args = @_;
	my $type = $args{type};
	my $term = $args{term};
	
	print_error("Must Supply A Serch Type, you gave '$type'") unless ($type);
	print_error("Must Supply A Serch Term, you gave '$term'") unless ($term);
	
	
	unless ( grep /^$type$/, keys(%search_types) ){
		print_error("Search Type '$type' is Not vaild, please fix the problem") unless ($type);
	}
	
	my $clean_term = clean_term($term);
	
	##Look at the different search terms and make sure the data looks ok
	if ($type eq 'Gene Symbol'){
		if ($clean_term =~ /\s/){
			print_error("Gene Symobols Cannot have any spaces '$clean_term'");
		}
	}elsif($type eq 'Swiss Prot Accession Number'){
		
		unless($clean_term =~ /^\w/){
			print_error("Swiss Prot Accession Does not look good '$clean_term'");
		}
	}elsif($type eq 'Accession Number'){
		
#		unless($clean_term =~ /^IPI\d+/){ print_error("IPI Accession Number does not look good '$clean_term'"); }

		
	}
	return ($type, $clean_term);
	
}

###############################################################################
#clean_term
#remove any bad characters
###############################################################################
sub clean_term{
	my $term = shift;
	
	$term =~ s/["'*.]//g; #Remove quotes, "*",  "."
	$term =~ s/^\s+//g; 		#Remove white space at the start
	$term =~ s/\s+$//g;		#Remove white space at the end
	
	if ($term =~ /^\%$/){ #check for just a wild card search
		print_error("Must provide more than just a wild card '$term' ") unless ($term);
	}
#unless ( grep /^$type$/, keys(%search_types) ){
  print_error("Search Term '$term' HAS BEEN DELETED") unless ($term);
#}
	return $term;
}

###############################################################################
#clean_action
#Make sure this is a param we know about
#Print error if not a good param
###############################################################################
sub clean_action{
	my $action_param = shift;
	
	#Add all the possible action parameters here
	my @good_actions = qw(Show_hits_form
						  Show_detail_form
						);
	if ( (grep {$_ eq $action_param} @good_actions) ){
		return $action_param;
	}else{
		print_error("ACTION PARAMETER '$action_param' IS NOT VALID");
	}

}




###############################################################################
#display_detail_form
###############################################################################
sub display_detail_form{

  my %args = @_;

  if ( $motif_type eq 'phospho' ) {
    $log->debug( "Phospho express" );
      display_phospho_detail_form( %args );
      return;
  }
  
  my %parameters = %{$args{ref_parameters}};
  my $ipi_data_id = $args{ipi_data_id}; 
    
  print_error("Must provide a ipi_id to display Glyco Info. '$ipi_data_id' is not valid")unless 
  ($ipi_data_id =~ /^\d+$/);
	
  #go an query the db, add the peptide features and make into a big Bio::Seq object
  my $glyco_o = new SBEAMS::Glycopeptide::Get_glyco_seqs( ipi_data_id => $ipi_data_id,
                                                              _sbeams => $sbeams );
  
  my $protein_map = make_protein_map_graphic ( glyco_o => $glyco_o );
  my $swiss_id = get_annotation(glyco_o   => $glyco_o,
								  anno_type => 'swiss_prot'
							     );

  my @prechecked = qw( sseq tmhmm glyco_site );
  my $html_protein_seq = $glyco_o->get_html_protein_seq( ref_parameters => \%parameters,
                                                         prechecked => \@prechecked
                                                       );

  my $protein_name = get_annotation(glyco_o   => $glyco_o,
									  anno_type => 'protein_name'
									  );
  my $ipi_acc = $glyco_o->ipi_accession();
    
  my $ipi_url = $glyco_o->make_url(term=> $glyco_o->ipi_accession(),
				     dbxref_tag => 'EBI_IPI'
  );
    
  my $swiss_prot_url = $glyco_o->make_url(term=>$swiss_id, 
                                     dbxref_tag => 'SwissProt'
                                    );
 

  my $spacer = $sbeams->getGifSpacer( 600 );
    my $protein_url = $glyco_o->get_atlas_link( name => $glyco_o->ipi_accession(), 
                                                type => 'image',
                                              onmouseover => 'View Peptide Atlas information' );

			
	## Print out the protein Information
  my $prot_info = join( "\n", 
    $q->Tr(
      $q->td({class=>'grey_header', colspan=>2}, "Protein Info"),),
    $q->Tr(
      $q->td({class=>'rev_gray_head'}, "ID"),
      $q->td("$ipi_url  [ View in Peptide Atlas: $protein_url ]")),
    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, "Protein Name"),
      $q->td( $protein_name )),

    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, 
              $glyco_o->linkToColumnText(display => "Protein Symbol",
                                         title   => "Protein Symbol Info", 
                                         column  => "protein_symbol", 
                                         table   => "GP_ipi_data" 
                 
                                   )),
      $q->td(get_annotation(glyco_o   => $glyco_o,
									  anno_type => 'symbol'
									  ) . $spacer
					   )
			  ),

    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, 
				$glyco_o->linkToColumnText(display => "Subcellular Location",
								 title   =>"Find More Info About the Subcellular Location Call", 
								 column  =>"cellular_location_id", 
								 table   => "GP_ipi_data" 
								 
								)),
				
      $q->td(get_annotation(glyco_o   => $glyco_o,
	        								  anno_type => 'cellular_location' ) )
			    ),

    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, "Swiss Prot ID"),
      $q->td($swiss_prot_url)
			  ),
    $q->Tr(
      $q->td({class=>'rev_gray_head'}, 
				$glyco_o->linkToColumnText(display => "Synonyms",
								 title   =>"Synonyms Info", 
								 column  =>"synonyms", 
								 table   => "GP_ipi_data" 
								 
								)),
      $q->td(get_annotation(glyco_o   => $glyco_o,
									  anno_type => 'synonyms'
									  )
					   )
			  ),
    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, "Protein Summary"),
      $q->td(get_annotation(glyco_o   => $glyco_o, anno_type => 'summary') )
			    ) 
    );  # End prot_info

## Display the predicted Peptide info

  my ( $tr, $link ) = $sbeams->make_table_toggle( name => '_gpre_prepep',
                                                visible => 1,
                                                tooltip => 'Show/Hide Section',
                                                imglink => 1,
                                                sticky => 1 );
    
  my $predicted_info = join( "\n", 
		$q->Tr(
				$q->td({class=>'grey_header', colspan=>2}, "$link Predicted N-linked Glycopeptides"),
			),
		  $q->Tr( "<TD COLSPAN=2 $tr>" .  $glyco_o->display_peptides('Predicted Peptides') . "</TD>" ), 
    ); # End predicted info

## Display Identified Peptides
  my ( $tr, $link ) = $sbeams->make_table_toggle( name => '_gpre_idpep',
                                                visible => 1,
                                                tooltip => 'Show/Hide Section',
                                                imglink => 1,
                                                sticky => 1 );
  my $identified_info = join( "\n", 
		$q->Tr(
				$q->td({class=>'grey_header', colspan=>2 }, "$link Observed Glycopeptides"),
			),
		$q->Tr( "<TD COLSPAN=2 $tr>" .  $glyco_o->display_peptides('Observed Peptides') . "</TD>" 
			),
    ); # End identified info

### Display the Amino Acid Sequence ###
  my %chk = ( predicted_pep => '', identified_pep => '', observed_pep => '',
             sseq => '', tmhmm => '', glyco_site => '' );

  if ( $parameters{redraw_protein_sequence} ) {
    for my $tag ( keys(%chk) ) {
      $chk{$tag} = 'checked' if $parameters{$tag};
    }
  } else { # fresh load
    for my $tag ( @prechecked )  { 
      $chk{$tag} = 'checked';
    }
  }


	
  my $sp = '&nbsp;';
  my $display_form = join( "\n", 
    $q->start_form(-action=>$q->script_name().'#protein_sequence'),
    $q->table( {border=>0, width=>'40%'},
    $q->Tr( 
    $q->Tr( 
      $q->td( {class=>'instruction_text', nowrap => 1 }, "Update:" ),
      $q->td( {class=>'pred_pep', nowrap => 1 }, "$sp Predicted <INPUT TYPE=CHECKBOX NAME=predicted_pep $chk{predicted_pep} ONCHANGE='toggle_state(predicted_pep);'></INPUT>" ),
#      $q->td( {class=>'iden_pep', nowrap => 1  },"$sp Identified <INPUT TYPE=CHECKBOX NAME=identified_pep $chk{identified_pep} ONCHANGE='toggle_state(identified_pep);'></INPUT>" ),
      $q->td( {class=>'obs_pep', nowrap => 1  },"$sp Observed <INPUT TYPE=CHECKBOX NAME=observed_pep $chk{observed_pep} ONCHANGE='toggle_state(observed_pep);'></INPUT>" ),
      $glyco_o->has_signal_sequence() ?  $q->td( {class=>'sig_seq', nowrap => 1 },"$sp Signal Sequence <INPUT TYPE=CHECKBOX NAME=sseq $chk{sseq} ONCHANGE='toggle_state(sseq);'></INPUT>" ) : '',
      $glyco_o->has_transmembrane_seq() ? $q->td( {class=>'tm_dom', nowrap => 1  },"$sp Transmembrane <INPUT TYPE=CHECKBOX NAME=tmhmm $chk{tmhmm} ONCHANGE='toggle_state(tmhmm);'></INPUT>" ) : '',
      $q->td( {class=>'glyco_seq', nowrap => 1 }, "$sp NxS/T site <INPUT TYPE=CHECKBOX NAME=glyco_site $chk{glyco_site} ONCHANGE='toggle_state(glyco_site);'></INPUT>" ),
          ),
      $q->hidden(-name=>'ipi_data_id', -value=>$ipi_data_id, -override => 1),
      $q->hidden(-name=>'redraw_protein_sequence', -value=>1),
          ),
    $q->end_form()
    ) # End table
  ); # End form

    my ( $seq_html, $toggle ) = $sbeams->make_toggle_section ( content => "$ipi_url|$protein_name <BR>$html_protein_seq <BR> $display_form",
                                                           visible => 1,
                                                            sticky => 1,
                                                            tooltip => 'Show/Hide Section',
                                                           imglink => 1,
                                                              name => '_gpre_protseq',);

    
  my $prot_seq = join( "\n", 
			$q->Tr(
				$q->td({class=>'grey_header', colspan=>2}, 
				"${toggle}Protein/Peptide Sequence"),
			),
			$q->Tr(
				$q->td({colspan=>2, class=>'sequence_font'}, $seq_html )
			),
    ); # End identified info

### Print Out the HTML to Make Dispaly the info About the the Protein and all it's Glyco-Peptides
  print $q->table({border=>0},
           $prot_info,
           $predicted_info,
           $identified_info,
           $prot_seq,
           $protein_map
				);#end_table	
		
#	print "$protein_map\n";	
	print $q->a({id=>'protein_sequence'});
	
	



	

} #end handle request

######################################################
#make imgae
#
#####################################################
sub make_protein_map_graphic {
  my %args = @_;
  my %tracks;

  my $seq =  $args{glyco_o}->seq_info();					
   
  my %colors = ( 'Signal Sequence' => 'lavender',
                 'Signal Sequence web' => '#CCCCFF',
                 Anchor => 'lavender',
                 Anchor => 'lavender',
                 Anchor_web => '#CCCCFF',
          Transmembrane => 'lightgreen',
          Transmembrane_web => '#CCFFCC',
          Intracellular => 'coral',
  $id_track_type => 'firebrick',
          Extracellular => 'mediumseagreen',
               Coverage => 'beige',
      $glyco_site_track => '#EE9999',
  $predicted_track_type => 'goldenrod',
   ambi_site_track      => 'lightyellow' );
  # Define CSS classes
  my $sp = '&nbsp;' x 4;
  my $style =<<"  END_STYLE";
  <STYLE>
   .obs_pep { background-color: $colors{$id_track_type} ;border-style: solid; border-color:gray; border-width: 1px  }
   .iden_pep { background-color: $colors{$id_track_type} ;border-style: solid; border-color:gray; border-width: 1px  }
   .pred_pep { background-color: $colors{$predicted_track_type} ;border-style: solid; border-color:gray; border-width: 1px  }
   .tm_dom { background-color: $colors{Transmembrane_web} ;border-style: solid; border-color:gray; border-width: 1px  }
   .in_dom { background-color: $colors{Intracellular} ;border-style: solid; border-color:gray; border-width: 1px  }
   .ex_dom { background-color: $colors{Extracellular} ;border-style: solid; border-color:gray; border-width: 1px  }
   .anc_seq { background-color: $colors{Anchor_web};border-style: solid; border-color:gray; border-width: 1px  }
   .sig_seq { background-color: $colors{'Signal Sequence web'};border-style: solid; border-color:gray; border-width: 1px  }
   .glyco_seq { background-color: $colors{$glyco_site_track};border-style: solid; border-color:gray; border-width: 1px  }
   .phospho { background-color: $colors{$glyco_site_track};border-style: solid; border-color:gray; border-width: 1px  }
   .ambiphospho { background-color: $colors{ambi_site_track};border-style: solid; border-color:gray; border-width: 1px; color: Black  }
   .pep_cov { background-color: $colors{Coverage};border-style: solid; border-color:gray; border-width: 1px  }
   .outline { border-style: solid; border-color:gray; border-width: 1px }
   .sm_txt {  font-family: Helvetica, Arial, sans-serif; font-size: 8pt}
  </STYLE>
  END_STYLE
  
  my $panel = Bio::Graphics::Panel->new( -length    => $seq->length,
                                         -key_style => 'between',
                                         -width     => 800,
                                         -pad_top   => 5,
                                             -empty_tracks => 'suppress',
                                         -pad_bottom => 5,
                                         -pad_left  => 10,
                                         -pad_right => 50 );
  
  my $length = $seq->length();
  my $ruler = Bio::SeqFeature::Generic->new( -start        => 2,
                                            -end          => $seq->length(),
                                            -display_name => $seq->display_id
                                           );

  my @features = $seq->all_SeqFeatures;
	
  # partition features by their primary tags
  my %sorted_features;
	for my $f (@features) {
    my $tag = $f->primary_tag;
    push @{ $sorted_features{ucfirst($tag)} }, $f;
  }

  $panel->add_track( $ruler,
                     -glyph  => 'anchored_arrow',
                     -tick   => 2,
                     -height => 8,
                     -key  => 'Sequence Position' );

  # Add Track for Identified Sequences
  # Adjust score to Protein Prohet score
  if ($sorted_features{$id_track_type}) {
    my %seen;
    my @non_redundant;
    my $max = 0;
    for my $f ( @{$sorted_features{$id_track_type}} ) {
#  $f->score( log( $f->score() ) );
      my $key = $f->seq()->seq() . $f->start() . $f->end;
      $max = ( $f->score() && $f->score() > $max ) ? $f->score() : $max; 
      next if $seen{$key};
      push @non_redundant, $f;
      $seen{$key}++;
    }
    $tracks{observed}++ if @non_redundant;
    $panel->add_track( \@non_redundant,
            -glyph       => 'graded_segments',
            -bgcolor     => $colors{$id_track_type},
            -fgcolor     => 'black',
            -font2color  => '#882222',
            -key         => $id_track_type,
            -bump        => 1,
            -bump_limit  => -1,
            -height      => 8,
            -label => \&peptide_label,
            -min_score => 0,
            -max_score => $max,
                   );
    delete $sorted_features{$id_track_type};
  }
   
  my $motif = $sbeamsMOD->get_current_motif_type();
  ##### Add Track for Predicted Sequences  -- taken out for now
   if ($sorted_features{$predicted_track_type} && $motif =~ /glycopeptide/ ) {
     $tracks{predicted}++;
     $panel->add_track($sorted_features{$predicted_track_type},
            -glyph       => 'segments',
            -bgcolor     => $colors{$predicted_track_type},
            -fgcolor     => 'black',
            -font2color  => 'red',
            -key         => $predicted_track_type,
            -bump        => 0,
            -height      => 8,
            -label       => 0,
#-description => \&peptide_label,
#            -min_score => 0,
#            -max_score => 1, #Remember the score is reversed down below so 0 is the best score and boldest color
                      );
     delete $sorted_features{$predicted_track_type};
   } 

   if ( $motif =~ /phospho/ ) {
     if ($sorted_features{'Phosphorylation Sites'}) {
       $tracks{phospho}++;
       $panel->add_track( $sorted_features{'Phosphorylation Sites'},
              -glyph       => 'segments',
              -bgcolor     => $colors{$glyco_site_track},
              -fgcolor     => 'black',
              -font2color  => 'red',
              -key         => 'Phosphorylation Sites',
              -bump        => 1,
              -bump_limit  => 2,
              -height      => 8,
				  		-label       => 0, #  sub {my $feature = shift; return $feature->start},
					  	-description => '',
                      );
      delete $sorted_features{'Phosphorylation sites'};
     } 
     if ($sorted_features{'Ambiguous Phosphorylation Sites'}) {
       $tracks{ambiphospho}++;
       $panel->add_track( $sorted_features{'Ambiguous Phosphorylation Sites'},
              -glyph       => 'segments',
              -bgcolor     => $colors{ambi_site_track},
              -fgcolor     => 'black',
              -font2color  => 'red',
              -key         => 'Ambiguous Phosphorylation Sites',
              -bump        => 1,
              -bump_limit  => 2,
              -height      => 8,
				  		-label       => 0, #  sub {my $feature = shift; return $feature->start},
					  	-description => '',
                      );
      delete $sorted_features{'Ambiguous Phosphorylation sites'};
     }
   } else {
     if ($sorted_features{$glyco_site_track}) {
       $tracks{phospho}++;
       $panel->add_track( $sorted_features{$glyco_site_track},
              -glyph       => 'segments',
              -bgcolor     => $colors{$glyco_site_track},
              -fgcolor     => 'black',
              -font2color  => 'red',
              -key         => $glyco_site_track,
              -bump        => 1,
              -bump_limit  => 2,
              -height      => 8,
				  		-label       => sub {my $feature = shift; return $feature->start},
					  	-description => '',
                      );
       delete $sorted_features{$glyco_site_track};
     }
   }

	# general case
  my $any = 0;
  my %lgd = ( Transmembrane => 'Transmembrane Domain',
              Extracellular => 'Outside membrane', 
              Intracellular => 'Inside membrane');

	for my $tag ( 'Signal Sequence', qw(Anchor Transmembrane Extracellular Intracellular) ) {
		#print "SORTED TAG '$tag'\n";
		 
    next if $tag =~ /cellular/ && !$sorted_features{Transmembrane};
 
    
		#feature objects have the score tag built in which is mapped to inbetween the low and high
		my $features = $sorted_features{$tag} || next;
    $any++;
#    $features ||= $sorted_features{ucfirst($tag)};
    
    $tracks{$tag}++;
		
		#make color gradient colors s
		my $track = $panel->add_track(
			$features,
			-glyph       => 'segments',
			-bgcolor     => $colors{$tag},
			-fgcolor     => 'black',
			-font2color  => 'red',
			-key         => "$lgd{$tag} (predicted)",
			-bump        => +1,
			-height      => 8,
		);
	}
  if ( !$any && 0 ) { # assume cyto!  - removed 2007/08 DSC
	#add the scale bar
  my $f = Bio::SeqFeature::Generic->new( -start        => 1,
                                          -end          => $seq->length(),
                                       );


  $tracks{Intracellular}++;
	$panel->add_track(
		$f,
		-glyph  => 'segments',
    -bgcolor     => $colors{Intracellular}, 
		-height      => 8,
		-bump   => 0 , )
  }
	
	#add the scale bar
	$panel->add_track(
		$ruler,
		-glyph  => 'arrow',
		-bump   => 0,
		-double => 1,
		-tick   => 2
	);


  # Create image map from panel objects. 
  # mouseover coords for segment glyphs
  my $pid = $$;
  my @objects = $panel->boxes();
  my $map = "<MAP NAME='$pid'>\n";
  for my $obj ( @objects ) {
    my $hkey_name = $obj->[0]->display_name();
    my $f = $obj->[0];
    my $coords = join( ", ", @$obj[1..4] );
    my $text = $f->start() . '-' . $f->end();

    eval {
      $text .= '  ' . $f->seq()->seq() if $f->seq();
    }; 
    if ( $@ ) {
      $log->error( $@ );
    }
    $map .= "<AREA SHAPE='RECT' COORDS='$coords' TITLE='$text'>\n";
  }
  $map .= '</MAP>';
  
  my $image_html = "<img BORDER=0 src='$HTML_BASE_DIR/$tmp_img_path/$file_name' ISMAP USEMAP='#$pid'  alt='Sorry No Img'>";
  

    # Set up graphic legend
  my @legend; 

  my %title = (
                sig_seq => "Signal peptide predicted from amino acid sequence",
                anc_seq => "Anchor sequence predicted from amino acid sequence",
                tm_dom => "Transmembrane region predicted from amino acid sequence",
                in_dom => "Predicted orientation inside, (intracellular for cell membrane proteins)",
                ex_dom =>  "Predicted orientation outside, (extracellular for cell membrane proteins)",
                pep_cov => "Cumulative sequence coverage",
              );


  push @legend, "<TR> <TD CLASS=obs_pep>$sp</TD> <TD class=sm_txt>Observed peptide: (# observations) </TD> </TR>\n" if $tracks{observed};
  push @legend, "<TR> <TD CLASS=obs_pep>$sp</TD> <TD class=sm_txt>Identified peptide: glycosite # (peptide prophet score) </TD> </TR>\n" if $tracks{identified};
  push @legend, "<TR> <TD CLASS=pred_pep>$sp</TD> <TD class=sm_txt>Predicted NxS/T motif tryptic peptide</TD> </TR>\n" if $tracks{predicted};
  push @legend, "<TR> <TD CLASS=glyco_seq>$sp</TD> <TD class=sm_txt>NxS/T Concensus glycosylation site</TD> </TR>\n"  if $tracks{glyco};
  push @legend, "<TR> <TD CLASS=phospho>$sp</TD> <TD class=sm_txt>Observed Phosphorylation Sites</TD> </TR>\n"  if $tracks{phospho};
  push @legend, "<TR> <TD CLASS=ambiphospho>$sp</TD> <TD class=sm_txt>Ambiguous Phosphorylation Sites</TD> </TR>\n"  if $tracks{'ambiphospho'};

  push @legend, "<TR> <TD CLASS=sig_seq>$sp</TD> <TD class=sm_txt><SPAN TITLE='$title{sig_seq}'>Signal sequence predicted by Signal P</SPAN></TD> </TR>\n" if $tracks{'Signal Sequence'}; 
  push @legend, "<TR> <TD CLASS=anc_seq>$sp</TD> <TD class=sm_txt><SPAN TITLE='$title{anc_seq}'>Anchor sequence predicted by Signal P</SPAN></TD> </TR>\n" if $tracks{anchor};
  push @legend, "<TR> <TD CLASS=tm_dom>$sp</TD> <TD class=sm_txt><SPAN TITLE='$title{tm_dom}'>Transmembrane domain predicted by TMHMM</SPAN></TD> </TR>\n" if $tracks{Transmembrane};
  push @legend, "<TR> <TD CLASS=ex_dom>$sp</TD> <TD class=sm_txt><SPAN TITLE='$title{ex_dom}'>Predicted as outside membrane by TMHMM </SPAN></TD> </TR>\n" if $tracks{Extracellular};
  push @legend, "<TR> <TD CLASS=in_dom>$sp</TD> <TD class=sm_txt><SPAN TITLE='$title{in_dom}'>Predicted as inside membrane by TMHMM</SPAN></TD> </TR>\n" if $tracks{Intracellular};

#  push @legend, "<TR> <TD CLASS=sig_seq>$sp</TD> <TD class=sm_txt>Signal sequence predicted by Signal P</TD> </TR>\n"  if $tracks{'Signal Sequence'};
#  push @legend, "<TR> <TD CLASS=anc_seq>$sp</TD> <TD class=sm_txt>Anchor sequence predicted by Signal P</TD> </TR>\n" if $tracks{anchor};
#  push @legend, "<TR> <TD CLASS=tm_dom>$sp</TD> <TD class=sm_txt>Transmembrane domain predicted by TMHMM</TD> </TR>\n" if $tracks{Transmembrane};
#  push @legend, "<TR> <TD CLASS=ex_dom>$sp</TD> <TD class=sm_txt>Extracellular domain predicted by TMHMM</TD> </TR>\n" if $tracks{Extracellular};
#  push @legend, "<TR> <TD CLASS=in_dom>$sp</TD> <TD class=sm_txt>Intracellular domain predicted by TMHMM</TD> </TR>\n" if $tracks{Intracellular};

  push @legend, "<TR> <TD CLASS=pep_cov>$sp</TD> <TD class=sm_txt>Protein coverage by observed peptides</TD> </TR>\n" if $tracks{coverage};


  

  my $legend = '';
  for my $item ( @legend ) {
    $legend .= $item;
  }
  
  # Print graphic to file
	open( OUT, ">$img_file" ) || die "$!: $img_file";
	binmode(OUT);
	print OUT $panel->png;
	close OUT;

  # Widget to allow show/hide of sequence graphic section
  my ( $tr, $link ) = $sbeams->make_table_toggle( name => 'getglyseqs_graphic',
                                                visible => 1,
                                                tooltip => 'Show/Hide Section',
                                                imglink => 1,
                                                sticky => 1 );
  # Generate and return HTML for graphic
  my $graphic =<<"  EOG";
  <TABLE width='100%'>
    <TR><TD CLASS='grey_header'>$link Protein/Peptide Map</TD></TR>
    <TR $tr> 
      <TD>
       $image_html
       $map
      </TD>
    </TR>
    <TR $tr>
      <TD COLSPAN=2 ALIGN=RIGHT>
        <TABLE BORDER=0 class=outline>
        $legend
        </TABLE> 
      </TD>
    </TR>
  </TABLE>
  $style
  EOG

  return $graphic;
  

}
#######################################################
#general_label
#######################################################
sub peptide_label {
     my $feature = shift;
     my $note = $feature->display_name();
     my $score = '';
    
     if ($feature->primary_tag eq $predicted_track_type){
     	#the GD graph score only maps from low to high.  Higher being better
     	#but the predicted glyco score is lower is better.  So re-map the score for the image
     	#but display the orginal score
     	$score = predicted_score($feature);
        $note .= sprintf(" GS = %01.2f",$score);
     }else{
     	#Identified score is peptide prophet
     	$score = $feature->score();
     	$note = $feature->start() . ' (' . sprintf("%01i",$score) . ')';
     }
    
     
     
     
     return $note;
}

######################################################
#predicted_score
######################################################
sub predicted_score {
	my $feat_o = shift;
	my $score = $feat_o->score();
	my $mapped_score = 1-$score;
	
	$feat_o->score($mapped_score);
	return $score;
}

######################################################
#get_annotation
######################################################
sub get_annotation {
	
	my %args = @_;
	my $glyco_o = $args{glyco_o};
	my $anno_type = $args{anno_type};
	
	#$glyco_o->get_protein_info(); 
    my $seq =  $glyco_o->seq_info();		
    my $info = '';
    
    #get an AnnotationCollectionI
	my $ac = $seq->annotation();
	
	#retrieves all the Bio::AnnotationI objects for one or more specific key(s).
	my @annotations = $ac->get_Annotations($anno_type);
	
	if ($annotations[0]){
		$info = $annotations[0]->hash_tree;
	}else{
		$info = "Cannot find Info for '$anno_type'";
	}
	
   
	return $info;
}


       # permitted_work_groups_ref=>['Glycopeptide_user','Glycopeptide_admin',
#
###############################################################################
#print_out_hits_page
#
###############################################################################
sub print_out_phospho_hits_page{
	
	my %args = @_;

	my @results_set = @{ $args{results_set_aref} };
	my %parameters = %{ $args{ref_parameters} };
  my $html;

	if (exists $parameters{similarity_score} && defined $parameters{similarity_score}){
		$html .= $q->p(
			$q->h3("Protein Similarity Score (Percent Match) <span class='lite_blue_bg'>" . $parameters{similarity_score} . "</span>"),
		);
	}
	
	$html .= $q->start_table();
  $html .= $q->Tr({class=>'rev_gray_head'},
			  $q->td({class=>'rev_gray_head'},'ID'),
			  $q->td({class=>'rev_gray_head'},'Protein Name'),
			  $q->td({class=>'rev_gray_head'},'Synonyms'),
			  $q->td({class=>'rev_gray_head'},'Protein Symbol'),
			  $q->td({class=>'rev_gray_head'},'Observed Peptides')
			);
#  $log->info( $html );
	my $cgi_url = "$base_url?action=Show_detail_form&ipi_data_id";
  my $protcnt = 0;
  my $pepprotcnt = 0;
  my $cutoff = $sbeamsMOD->get_current_prophet_cutoff();
  my $pepcnt = 0;
  my @symbols;
  my $current = '';
  my $color = 'E0E0E0';
	foreach my $h_ref (@results_set){
		my $ipi_id = $h_ref->{ipi_data_id};
		my $ipi_acc = $h_ref->{ipi_accession_number};
    $current ||= $ipi_acc;
    if ( $current ne $ipi_acc ) {
      $color = ( $color eq 'E0E0E0' ) ? 'F5F5F5' : 'E0E0E0';
    }
    $current = $ipi_acc;
		my $num_identified = $h_ref->{num_observed};
		my $protein_name = nice_term_print($h_ref->{protein_name});
		my $protein_sym = $h_ref->{protein_symbol};
		my $synonyms = $h_ref->{synonyms};
    push @symbols, $protein_sym if $protein_sym;
    $protcnt++;
    $pepprotcnt++ if $num_identified;
    $pepcnt += $num_identified;
		$html .= join( "\n", $q->Tr( {BGCOLOR=>$color},
			    $q->td(
			    	$q->a({href=>"$cgi_url=$ipi_id"},$ipi_acc)
			    ),
			    $q->td($protein_name),
			    $q->td($synonyms),
			    $q->td($protein_sym),
			    $q->td({ALIGN=>'right'},$num_identified)
          )
        );
	}
	$html .= "</table>";

  my $organism = 'human';
  my $gXML = $sbeams->getGaggleXML( object => 'namelist', 
                                      type => 'direct',
                                      name => "Gene symbols",
                                      data => \@symbols,
                                     start => 1, 
                                       end => 1,
                                     organism => $organism );
  $html .= "\n$gXML\n";

  my $type = ( check_search_params(\%parameters) eq 'text' ) ? 
                                                      $parameters{search_type} :
                                                       'sequence';
  my $value = '';
  if ($type eq 'sequence') {
    $value = $parameters{sequence_search};
    if ( length($value) > 12 ) {
      $value = substr($value, 0, 12) . '...';
    }
  } else {
    $value = $parameters{search_term};
  }

  my $ofwhich = "of which $pepprotcnt";
  my $contain = ( $pepprotcnt > 1 ) ? 'contain' : 'contains';
  if ( $pepprotcnt == $protcnt || $pepcnt == 0 ) {
    $ofwhich = 'which';
  }

  my $stats = qq~
  <BR><FONT COLOR=GREEN>
  Your search for proteins with $type = 
  '$value'  found  $protcnt proteins $ofwhich $contain
  a total of $pepcnt peptides at a prophet cutoff of $cutoff
  </FONT>
  <BR>
  <BR>
  ~;
  print "$stats $html";
}



###############################################################################
#display_detail_form
###############################################################################
sub display_phospho_detail_form{

  my %args = @_;
  
  my %parameters = %{$args{ref_parameters}};
  my $ipi_data_id = $args{ipi_data_id}; 
    
  print_error("Must provide a ipi_id to display Glyco Info. '$ipi_data_id' is not valid")unless 
  ($ipi_data_id =~ /^\d+$/);
	
  #go an query the db, add the peptide features and make into a big Bio::Seq object
  my $glyco_o = new SBEAMS::Glycopeptide::Get_glyco_seqs( ipi_data_id => $ipi_data_id,
                                                              _sbeams => $sbeams );
  
  my $protein_map = make_protein_map_graphic ( glyco_o => $glyco_o );
  my $swiss_id = get_annotation(glyco_o   => $glyco_o,
								  anno_type => 'swiss_prot'
							     );

  my @prechecked = qw( observed_pep tmhmm phospho ambiphospho );
  my $html_protein_seq = $glyco_o->get_html_protein_seq( ref_parameters => \%parameters,
                                                         prechecked => \@prechecked
                                                       );

  my $protein_name = get_annotation(glyco_o   => $glyco_o,
									  anno_type => 'protein_name'
									  );

  my $organism = $sbeamsMOD->get_current_organism();
  my $consensus = $sbeamsMOD->get_build_consensus_library();

  my $pseq = $glyco_o->seq_info()->seq();
  my $synonym = get_annotation(glyco_o   => $glyco_o, anno_type => 'synonyms' );
  my $ipi_acc = $glyco_o->ipi_accession();
  my $keggname = ( $organism eq 'Drosophila' ) ? $synonym : $ipi_acc;
  my $kegglink = getKeggLink( name => $keggname, organism => $organism );
  my $cytolink = getCytoLink( acc => $ipi_acc );
  my $scanlink = getScansiteForm( seq => $pseq, name => $ipi_acc );
  my $mrmlink = "<A HREF='ViewMRMList?NIST_library_id=$consensus&action=QUERY;protein_name_constraint=$ipi_acc'>view transitions</A>";

  $log->debug( "making the ortho link!" );
  my $ortholink = getOrthologLink( id => $ipi_data_id );
    
  my $ipi_url = $ipi_acc;
  if ( $organism eq 'Drosophila' ) {
    $ipi_url = getFlybaseLink( name => $ipi_acc );
  } elsif ( $organism eq 'Yeast' ) {
    $ipi_url = getSGDLink( name => $ipi_acc );
  }
    
  my $swiss_prot_url = $glyco_o->make_url(term=>$swiss_id, 
                                     dbxref_tag => 'SwissProt'
                                    );
 

  my $spacer = $sbeams->getGifSpacer( 600 );
    my $protein_url = $glyco_o->get_atlas_link( name => $glyco_o->ipi_accession(), 
                                                type => 'image',
                                              onmouseover => 'View Peptide Atlas information' );

			
	## Print out the protein Information
  my $sp = '&nbsp;' x 2;
  my $prot_info = join( "\n", 
    $q->Tr(
      $q->td({class=>'grey_header', colspan=>2}, "Protein Info "),),
    $q->Tr(
      $q->td({class=>'rev_gray_head'}, "ID"),
      $q->td({nowrap=>1}, "$ipi_url $kegglink $cytolink $ortholink $scanlink ")),
    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, "Protein Name"),
      $q->td( $protein_name )),

    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, 
              $glyco_o->linkToColumnText(display => "Protein Symbol",
                                         title   => "Protein Symbol Info", 
                                         column  => "protein_symbol", 
                                         table   => "GP_ipi_data" 
                 
                                   )),
      $q->td(get_annotation(glyco_o   => $glyco_o,
									  anno_type => 'symbol'
									  ) . $spacer
					   )
			  ),

    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, 
				$glyco_o->linkToColumnText(display => "Subcellular Location",
								 title   =>"Find More Info About the Subcellular Location Call", 
								 column  =>"cellular_location_id", 
								 table   => "GP_ipi_data" 
								 
								)),
				
      $q->td(get_annotation(glyco_o   => $glyco_o,
	        								  anno_type => 'cellular_location' ) )
			    ),

    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, "Swiss Prot ID"),
      $q->td($swiss_prot_url)
			  ),
    $q->Tr(
      $q->td({class=>'rev_gray_head'}, 
				$glyco_o->linkToColumnText(display => "Synonyms",
								 title   =>"Synonyms Info", 
								 column  =>"synonyms", 
								 table   => "GP_ipi_data" 
								 
								)),
      $q->td(get_annotation(glyco_o   => $glyco_o,
									  anno_type => 'synonyms'
									  )
					   )
			  ),
    $q->Tr(
      $q->td({class=>'rev_gray_head', nowrap=>1}, "Protein Summary"),
      $q->td(get_annotation(glyco_o   => $glyco_o, anno_type => 'summary') )
			    ) 
    );  # End prot_info

## Display the predicted Peptide info

  my $drek  =<<'END_DREK';
  my ( $tr, $link ) = $sbeams->make_table_toggle( name => '_gpre_prepep',
                                                visible => 1,
                                                tooltip => 'Show/Hide Section',
                                                imglink => 1,
                                                sticky => 1 );
    
  my $predicted_info = join( "\n", 
		$q->Tr(
				$q->td({class=>'grey_header', colspan=>2}, "$link Predicted N-linked Glycopeptides"),
			),
		  $q->Tr( "<TD COLSPAN=2 $tr>" .  $glyco_o->display_peptides('Predicted Peptides') . "</TD>" ), 
    ); # End predicted info
END_DREK

## Display Identified Peptides
  my ( $tr, $link ) = $sbeams->make_table_toggle( name => '_gpre_idpep',
                                                visible => 1,
                                                tooltip => 'Show/Hide Section',
                                                imglink => 1,
                                                sticky => 1 );
  my $identified_info = join( "\n", 
		$q->Tr(
				$q->td({class=>'grey_header', colspan=>2 }, "$link Observed Phosphopeptides $mrmlink"),
			),
		$q->Tr( "<TD COLSPAN=2 $tr>" .  $glyco_o->display_peptides('Observed Phosphopeptides') . "</TD>" 
			),
    ); # End identified info

### Display the Amino Acid Sequence ###
  my %chk = ( predicted_pep => '', identified_pep => '', observed_pep => '',
             sseq => '', tmhmm => '', glyco_site => '', phospho => '', ambiphosph => '' );

  if ( $parameters{redraw_protein_sequence} ) {
    for my $tag ( keys(%chk) ) {
      $chk{$tag} = 'checked' if $parameters{$tag};
    }
  } else { # fresh load
    for my $tag ( @prechecked )  { 
      $chk{$tag} = 'checked';
    }
  }


	
  my $sp = '&nbsp;';
  my $display_form = join( "\n", 
    $q->start_form(-action=>$q->script_name().'#protein_sequence'),
    $q->table( {border=>0, width=>'40%'},
    $q->Tr( 
    $q->Tr( 
      $q->td( {class=>'instruction_text', nowrap => 1 }, "Update:" ),
#      $q->td( {class=>'pred_pep', nowrap => 1 }, "$sp Predicted <INPUT TYPE=CHECKBOX NAME=predicted_pep $chk{predicted_pep} ONCHANGE='toggle_state(predicted_pep);'></INPUT>" ),
#      $q->td( {class=>'iden_pep', nowrap => 1  },"$sp Identified <INPUT TYPE=CHECKBOX NAME=identified_pep $chk{identified_pep} ONCHANGE='toggle_state(identified_pep);'></INPUT>" ),
      $q->td( {class=>'obs_pep', nowrap => 1  },"$sp Observed <INPUT TYPE=CHECKBOX NAME=observed_pep $chk{observed_pep} ONCHANGE='toggle_state(observed_pep);'></INPUT>" ),
      $glyco_o->has_signal_sequence() ?  $q->td( {class=>'sig_seq', nowrap => 1 },"$sp Signal Sequence <INPUT TYPE=CHECKBOX NAME=sseq $chk{sseq} ONCHANGE='toggle_state(sseq);'></INPUT>" ) : '',
      $glyco_o->has_transmembrane_seq() ? $q->td( {class=>'tm_dom', nowrap => 1  },"$sp Transmembrane <INPUT TYPE=CHECKBOX NAME=tmhmm $chk{tmhmm} ONCHANGE='toggle_state(tmhmm);'></INPUT>" ) : '',
      $q->td( {class=>'phospho', nowrap => 1 }, "Phosphorylation Site <INPUT TYPE=CHECKBOX NAME=phospho $chk{phospho} ONCHANGE='toggle_state(phospho);'></INPUT>" ),
      $q->td( {class=>'ambiphospho', nowrap => 1 }, "Ambiguous Phosphorylation <INPUT TYPE=CHECKBOX NAME=ambiphospho $chk{ambiphospho} ONCHANGE='toggle_state(ambiphospho);'></INPUT>" ),
          ),
      $q->hidden(-name=>'ipi_data_id', -value=>$ipi_data_id, -override => 1),
      $q->hidden(-name=>'redraw_protein_sequence', -value=>1),
          ),
    $q->end_form()
    ) # End table
  ); # End form

    my ( $seq_html, $toggle ) = $sbeams->make_toggle_section ( content => "$ipi_url|$protein_name <BR>$html_protein_seq <BR> $display_form",
                                                           visible => 1,
                                                            sticky => 1,
                                                            tooltip => 'Show/Hide Section',
                                                           imglink => 1,
                                                              name => '_gpre_protseq',);

    
  my $prot_seq = join( "\n", 
			$q->Tr(
				$q->td({class=>'grey_header', colspan=>2}, 
				"${toggle}Protein/Peptide Sequence"),
			),
			$q->Tr(
				$q->td({colspan=>2, class=>'sequence_font'}, $seq_html )
			),
    ); # End identified info

### Print Out the HTML to Make Display the info About the the Protein and all it's Glyco-Peptides
  print $q->table({border=>0},
           $prot_info,
           $identified_info,
           $prot_seq,
				);#end_table	
		
  # This is in its own table to keep if from stretching too much.
  print "$protein_map\n";	
  print $q->a({id=>'protein_sequence'});

} #end display_phospho


sub getFlybaseLink {
  my %args = @_;
  for my $arg ( qw( name ) ) {
    return "" unless $args{$arg};
  }
  my $base = 'http://flybase.org/cgi-bin/uniq.html?species=Dmel;Submit=Go;db=fbgn;cs=yes;caller=genejump;context=';
  
  return "<A HREF=${base}$args{name} TITLE='View protein info at Flybase'>$args{name}</A>";
}

sub getSGDLink {
  my %args = @_;
  for my $arg ( qw( name ) ) {
    return "" unless $args{$arg};
  }
  my $base = 'http://db.yeastgenome.org/cgi-bin/locus.pl?locus=';
  
  return "<A HREF=${base}$args{name} TITLE='View protein info at SGD'>$args{name}</A>";

}

sub getCytoLink {
  my %args = @_;
  for my $arg ( qw( acc ) ) {
    return "" unless $args{$arg};
  }
  $args{name} =~ s/(CG\d+)(-P.)*/$1/;
  my $img = "$HTML_BASE_DIR/images/cyto_tiny.png";
  my $link_base = 'getCytoscapeWebstart?apply_action=gene_list&accession=';
  return "<A HREF=$link_base$args{acc}><IMG BORDER=0 TITLE='Start Cytoscape network with this gene' SRC=$img></A>";
}

sub getOrthologLink {
  my %args = @_;
  return '' unless $args{id};

  my ($exists) = $sbeams->selectrow_array( <<"  END" );
  SELECT count(*) FROM $TBGP_ORTHOLOG_TO_IPI
  WHERE ipi_data_id = $args{id}
  END
  $log->debug(  <<"  END" );
  SELECT count(*) FROM $TBGP_ORTHOLOG_TO_IPI
  WHERE ipi_data_id = $args{id}
  END

  return '' unless $exists;

  return qq ~<A HREF="viewOrthologs?ipi_data_id=$args{id}" TITLE="View orthologs/homolog information ($exists groups)"><IMG BORDER=0 SRC="$HTML_BASE_DIR/images/OrthoMCL.jpg"></A>~;
}

sub getKeggLink {
  my %args = @_;
  for my $arg ( qw( name ) ) {
    return "" unless $args{$arg};
  }
  if( $args{organism} eq 'Drosophila' ) {
    $args{name} =~ s/(CG\d+)(-P.)*/$1/;
    $args{name} = 'Dmel' . $args{name};
  }
  my $img = "$HTML_BASE_DIR/images/kegg_sm.gif";
  return "<A HREF=showPathways?ga=${args{name}}><IMG BORDER=0 TITLE='View KEGG pathways for this gene' SRC=$img></A>";
}


sub getScansiteForm {
  my %args = @_;
  for my $arg ( qw( seq name ) ) {
    return "" unless $args{$arg};
  }

#  <FORM NAME="scanners" ACTION="http://scansite.mit.edu/cgi-bin/motifscan_seq" METHOD=POST ONSUBMIT="alert('phooey')">

  my $img = "$HTML_BASE_DIR/images/scansite.png";
  return <<"  END";
  <A ONCLICK="submit_scansite();"><IMG BORDER=0 TITLE="Search protein sequence at scansite" SRC=$img></A>
  <FORM NAME="scansite" ACTION="http://scansite.mit.edu/cgi-bin/motifscan_seq" METHOD="POST" TARGET="scansite">
  <INPUT TYPE=HIDDEN NAME=sequence VALUE="$args{seq}"></INPUT>
  <INPUT TYPE=HIDDEN NAME=protein_id VALUE="$args{name}"></INPUT>
  <INPUT TYPE=HIDDEN NAME=motif_option VALUE="select"></INPUT>
  <INPUT TYPE=HIDDEN NAME=groups VALUE="1"></INPUT>
  <INPUT TYPE=HIDDEN NAME=groups VALUE="2"></INPUT>
  <INPUT TYPE=HIDDEN NAME=groups VALUE="5"></INPUT>
  <INPUT TYPE=HIDDEN NAME=groups VALUE="7"></INPUT>
  <INPUT TYPE=HIDDEN NAME=groups VALUE="8"></INPUT>
  <INPUT TYPE=HIDDEN NAME=groups VALUE="9"></INPUT>
  <INPUT TYPE=HIDDEN NAME=groups VALUE="11"></INPUT>
  <INPUT TYPE=HIDDEN NAME=stringency VALUE="Medium"></INPUT>
  <INPUT TYPE=HIDDEN NAME=domain_flag VALUE="on"></INPUT>
  <INPUT TYPE=HIDDEN NAME=submitme VALUE="Submit Request"></INPUT>
  </FORM>
  <SCRIPT LANGUAGE="javascript">
  function submit_scansite() {
    document.scansite.submit();
  }
  </SCRIPT>
  END
}