#!/usr/local/bin/perl

###############################################################################
# $Id: Glyco_prediction.cgi 4280 2006-01-13 06:02:10Z dcampbel $
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
use lib qw (../../lib/perl);
use CGI::Carp qw(fatalsToBrowser croak);
use Data::Dumper;

use SBEAMS::Connection qw($q $log);
use SBEAMS::Connection::Settings;
use SBEAMS::Connection::Tables;
use SBEAMS::Connection::TabMenu;

use SBEAMS::Glycopeptide;
use SBEAMS::Glycopeptide::Settings;
use SBEAMS::Glycopeptide::Tables;

use SBEAMS::Glycopeptide::Get_glyco_seqs;
use SBEAMS::Glycopeptide::Glyco_query;

# Global Variables
###############################################################################
#
my $sbeams = new SBEAMS::Connection;
$sbeams->setSBEAMS_SUBDIR($SBEAMS_SUBDIR);

my $sbeamsMOD = new SBEAMS::Glycopeptide;
$sbeamsMOD->setSBEAMS($sbeams);

my $glyco_query_o = new SBEAMS::Glycopeptide::Glyco_query;
$glyco_query_o->setSBEAMS($sbeams);

my $predicted_track_type = "Predicted Peptides";
my $id_track_type 		 = 'Identified Peptides';


main();


###############################################################################
# Main Program:
#
# Call $sbeams->Authentication and stop immediately if authentication
# fails else continue.
###############################################################################
sub main 
{ 
  my $current_username;
  # Authenticate and exit if a username is not returned
  $current_username = $sbeams->Authenticate(
        permitted_work_groups_ref=>['Glycopeptide_user','Glycopeptide_admin','Glycopeptide_readonly'],
        allow_anonymous_access=>0 ) || exit;
  $sbeams->set_page_message( type => 'Info', msg => 'Hello World' );

  #### Read in the default input parameters
  my $params = process_params();

  ## get project_id to send to HTMLPrinter display
  my $project_id = $sbeams->getCurrent_project_id();

   

  $sbeamsMOD->display_page_header(project_id => $project_id);
  my $content = get_settings_form( $params );
  print "$content";
  $sbeamsMOD->display_page_footer();

} # end main

sub process_params {
  my $params = {};
  # Process parameters
  $sbeams->parse_input_parameters( parameters_ref => $params,
                                                 q => $q );
  # Process "state" parameters
  $sbeams->processStandardParameters( parameters_ref => $params );
  return $params;
}

sub get_settings_form {
  my $params = shift;
  my $content = $sbeams->getGifSpacer(800);

  my $table = SBEAMS::Connection::DataTable->new( BORDER => 1 );
  $table->addRow( ['Available Builds'] ); 
  $table->setColAttr( ROWS => [ $table->getRowNum() ], COLS => [1], COLSPAN => 3 ); 

  my $sql =<<"  END";
  SELECT unipep_build_id, build_name, motif_type, 
         organism_name, us.sample_id, sample_name, sample_description
  FROM $TBGP_UNIPEP_BUILD u 
  JOIN $TBGP_IPI_VERSION i ON i.ipi_version_id = u.ipi_version 
  JOIN $TB_ORGANISM o ON o.organism_id = i.organism_id
  JOIN $TBGP_BUILD_TO_SEARCH bts ON bts.build_id = u.unipep_build_id
  JOIN $TBGP_PEPTIDE_SEARCH ps ON bts.search_id = ps.peptide_search_id
  JOIN $TBGP_UNIPEP_SAMPLE us ON us.sample_id = ps.sample_id
  ORDER BY u.is_default DESC, us.sample_name ASC
  END

  my @rows = $sbeams->selectSeveralColumns( $sql );

  # collapse on build
  my %builds;
  my @b;
  for my $row ( @rows ) {
    unless ( $builds{$row->[0]} ) {
      $builds{$row->[0]} = [];
      push @b, $row->[0];
    }
    push @{$builds{$row->[0]}}, $row;
  }
  my $sel = 'checked';
  my @spans;
  for my $b ( @b ) {
    my @rows = @{$builds{$b}};
    my $row = shift @rows;
    my ( $bld_id, $ver, $motif, $org, $smp_id, $smp_name, $smp_desc ) = @$row;
    my $tgl_name = 'smpl_toggle_' . $smp_id;
    my $radio = "<INPUT TYPE=radio NAME=build_id VALUE=$bld_id $sel ONCLICK=toggle_tbl('$tgl_name');>$ver";
    $table->addRow( [$radio, $org, $motif] ); 
    $table->setColAttr( ROWS => [ $table->getRowNum() ], COLS => [1], ALIGN=>'LEFT'  ); 

    if ( 0 ) {
    
    my $chk = 'checked';
    my $chk_name = $bld_id . '_samples';
    my $samples = "<INPUT TYPE=checkbox $chk NAME='$chk_name' VALUE=$smp_id> $smp_name ($smp_desc)<BR>";
    while ( @rows ) {
      my $row = shift @rows;
      my ( $bld_id, $ver, $motif, $org, $smp_id, $smp_name, $smp_desc ) = @$row;
      $samples .= "<INPUT TYPE=checkbox $chk NAME='{$bld_id}_samples' VALUE=$smp_id> $smp_name ($smp_desc) <BR>";
    }
    my ( $td, $link ) = $sbeams->make_table_toggle( name => $tgl_name,
                                                  sticky => 0,
                                                 visible => ( $sel ) ? 1 : 0,
                                                 as_hashref => 1,
                                                 imglink => 1
                                                  );
    $sel = '';
    push @spans, $samples, $td;

#    my @guts = @{$builds{$k}};
#    $log->debug( "$k => " . join( "\t", @guts ) );
  }
  my $cnt = 0;
  while ( @spans ) {
    $cnt++;
    my $samples = shift @spans;
    my $td = shift @spans;
    $table->addRow( [$samples] ); 
    $log->debug( %$td );
    $table->setColAttr( ROWS => [ $table->getRowNum() ], COLS => [1], COLSPAN=>3, ALIGN=>'LEFT', %$td  ); 
    die if $cnt > 100;
  }

  }

  my $submit = join " ", $sbeams->getFormButtons(types => [qw(submit reset)]);

  return <<"  END";
  <FORM NAME=unipep_settings METHOD=POST>
  $content;
  <BR>$table
  $submit
  END
  
}
