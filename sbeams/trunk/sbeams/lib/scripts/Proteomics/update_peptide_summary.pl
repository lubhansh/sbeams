#!/usr/local/bin/perl -w

###############################################################################
# Program     : update_peptide_summary.pl
# Author      : Eric Deutsch <edeutsch@systemsbiology.org>
# $Id$
#
# Description : This script updates an "Annotated Peptide Database"
#               peptide_summary based on a query of certain experiments
#
###############################################################################


###############################################################################
# Generic SBEAMS setup for all the needed modules and objects
###############################################################################
use strict;
use Getopt::Long;
use FindBin;
use Data::Dumper;

use lib qw (../perl ../../perl);
use vars qw ($sbeams $sbeamsMOD $q
             $PROG_NAME $USAGE %OPTIONS $QUIET $VERBOSE $DEBUG $TESTONLY
             $current_contact_id $current_username
            );


#### Set up SBEAMS core module
use SBEAMS::Connection;
use SBEAMS::Connection::Settings;
use SBEAMS::Connection::Tables;

use SBEAMS::Proteomics;
use SBEAMS::Proteomics::Settings;
use SBEAMS::Proteomics::Tables;

$sbeams = SBEAMS::Connection->new();
$sbeamsMOD = SBEAMS::Proteomics->new();
$sbeamsMOD->setSBEAMS($sbeams);


###############################################################################
# Set program name and usage banner for command like use
###############################################################################
$PROG_NAME = $FindBin::Script;
$USAGE = <<EOU;
Usage: $PROG_NAME [OPTIONS]
Options:
  --verbose n         Set verbosity level.  default is 0
  --quiet             Set flag to print nothing at all except errors
  --debug n           Set debug flag
  --testonly          Do not actually write to the database
  --delete_existing   Delete the existing peptides for this set before
                      loading.  Normally, if there are existing peptides,
                      the load is blocked.
  --update_existing   Update the existing peptides set with information
                      from the new query
  --summary_name      The name of the peptide summary that is to be worked
                      on; all are checked if none is provided
  --check_status      Is set, nothing is actually done, but rather the
                      summaries are verified

 e.g.:  $PROG_NAME --summary_name "Human Peptide Database"

EOU


#### If no parameters are given, print usage information
unless ($ARGV[0]){
  print "$USAGE";
  exit;
}

#### Process options
unless (GetOptions(\%OPTIONS,"verbose:s","quiet","debug:s","testonly",
  "delete_existing","update_existing","",
  "summary_name:s","check_status")) {
  print "$USAGE";
  exit;
}

$VERBOSE = $OPTIONS{"verbose"} || 0;
$QUIET = $OPTIONS{"quiet"} || 0;
$DEBUG = $OPTIONS{"debug"} || 0;
$TESTONLY = $OPTIONS{"testonly"} || 0;
if ($DEBUG) {
  print "Options settings:\n";
  print "  VERBOSE = $VERBOSE\n";
  print "  QUIET = $QUIET\n";
  print "  TESTONLY = $TESTONLY\n";
}


###############################################################################
# Set Global Variables and execute main()
###############################################################################
main();
exit(0);


###############################################################################
# Main Program:
#
# Call $sbeams->Authenticate() and exit if it fails or continue if it works.
###############################################################################
sub main {

  #### Do the SBEAMS authentication and exit if a username is not returned
  exit unless ($current_username = $sbeams->Authenticate(
    work_group=>'Proteomics_admin',
  ));


  $sbeams->printPageHeader() unless ($QUIET);
  handleRequest();
  $sbeams->printPageFooter() unless ($QUIET);


} # end main



###############################################################################
# handleRequest
###############################################################################
sub handleRequest { 
  my %args = @_;


  #### Define standard variables
  my ($i,$element,$key,$value,$line,$result,$sql);


  #### Set the command-line options
  my $delete_existing = $OPTIONS{"delete_existing"} || '';
  my $update_existing = $OPTIONS{"update_existing"} || '';
  my $check_status = $OPTIONS{"check_status"} || '';
  my $summary_name = $OPTIONS{"summary_name"} || '';


  #### Print out the header
  unless ($QUIET) {
    $sbeams->printUserContext();
    print "\n";
  }


  #### Define a scalar and array of biosequence_set_id's
  my ($peptide_summary_id,$n_peptide_summaries);
  my @peptide_summary_ids;


  #### If there was a summary_name specified, identify it
  if ($summary_name) {
    $sql = qq~
          SELECT peptide_summary_id
            FROM $TBAPD_PEPTIDE_SUMMARY
           WHERE peptide_summary_name = '$summary_name'
             AND record_status != 'D'
    ~;

    @peptide_summary_ids = $sbeams->selectOneColumn($sql);
    $n_peptide_summaries = @peptide_summary_ids;

    die "No peptide_summaries found with summary_name = '$summary_name'"
      if ($n_peptide_summaries < 1);
    die "Too many peptide_summaries found with summary_name = '$summary_name'"
      if ($n_peptide_summaries > 1);


  #### If there was NOT a summary_name specified, scan for all available ones
  } else {
    $sql = qq~
          SELECT peptide_summary_id
            FROM $TBAPD_PEPTIDE_SUMMARY
           WHERE record_status != 'D'
    ~;

    @peptide_summary_ids = $sbeams->selectOneColumn($sql);
    $n_peptide_summaries = @peptide_summary_ids;

    die "No peptide_summaries found in this database"
      if ($n_peptide_summaries < 1);

  }


  #### Loop over each peptide_summary, determining its status and processing
  #### it if desired
  print "N Peptides  Peptide Summary Name\n";
  print "----------  -----------------------------------\n";
  foreach $peptide_summary_id (@peptide_summary_ids) {
    my $status = getPeptideSummaryStatus(
      peptide_summary_id => $peptide_summary_id);
    printf("%10d  %s\n",$status->{n_rows},$status->{peptide_summary_name});

    #### If we're not just checking the status
    unless ($check_status) {
      my $do_load = 0;
      $do_load = 1 if ($status->{n_rows} == 0);
      $do_load = 1 if ($update_existing);
      $do_load = 1 if ($delete_existing);

      #### If it's determined that we need to do a load, do it
      if ($do_load) {
        $result = updatePeptideSummary(
          peptide_summary_name=>$status->{peptide_summary_name},
        );
      }

    }

  }


  return;

}



###############################################################################
# getPeptideSummaryStatus
###############################################################################
sub getPeptideSummaryStatus {
  my %args = @_;
  my $SUB_NAME = 'getPeptideSummaryStatus';


  #### Decode the argument list
  my $peptide_summary_id = $args{'peptide_summary_id'}
   || die "ERROR[$SUB_NAME]: peptide_summary_id not passed";


  #### Define standard variables
  my ($i,$element,$key,$value,$line,$result,$sql);


  #### Get information about this biosequence_set_id from database
  $sql = qq~
          SELECT peptide_summary_id,peptide_summary_name,experiment_list,
                 minimum_probability
            FROM $TBAPD_PEPTIDE_SUMMARY
           WHERE peptide_summary_id = '$peptide_summary_id'
  ~;
  my @rows = $sbeams->selectSeveralColumns($sql);


  #### Put the information in a hash
  my %status;
  $status{peptide_summary_id} = $rows[0]->[0];
  $status{peptide_summary_name} = $rows[0]->[1];
  $status{experiment_list} = $rows[0]->[2];
  $status{minimum_probability} = $rows[0]->[3];


  #### Get the number of rows for this biosequence_set_id from database
  $sql = qq~
          SELECT count(*) AS 'count'
            FROM $TBAPD_PEPTIDE
           WHERE peptide_summary_id = '$peptide_summary_id'
  ~;
  my ($n_rows) = $sbeams->selectOneColumn($sql);


  #### Put the information in a hash
  $status{n_rows} = $n_rows;


  #### Return information
  return \%status;

}



###############################################################################
# updatePeptideSummary
###############################################################################
sub updatePeptideSummary {
  my %args = @_;
  my $SUB_NAME = 'updatePeptideSummary';


  #### Decode the argument list
  my $peptide_summary_name = $args{'peptide_summary_name'}
   || die "ERROR[$SUB_NAME]: peptide_summary_name not passed";


  #### Define standard variables
  my ($i,$element,$key,$value,$line,$result,$sql);


  #### Set the command-line options
  my $delete_existing = $OPTIONS{"delete_existing"};
  my $update_existing = $OPTIONS{"update_existing"};


  #### Set the set_name
  $sql = qq~
          SELECT peptide_summary_name,peptide_summary_id
            FROM $TBAPD_PEPTIDE_SUMMARY
           WHERE peptide_summary_name = '$peptide_summary_name'
             AND record_status != 'D'
  ~;

  my %summary_names = $sbeams->selectTwoColumnHash($sql);
  my $peptide_summary_id = $summary_names{$peptide_summary_name};


  #### If we didn't find it then bail
  unless ($peptide_summary_id) {
    die("Unable to determine a peptide_summary_id for '$peptide_summary_name'. " .
      "A record for this peptide_summary must already have been entered " .
      "before the peptides may be loaded.");
  }


  #### Test if there are already sequences for this biosequence_set
  $sql = qq~
          SELECT count(*) AS 'count'
            FROM $TBAPD_PEPTIDE
           WHERE peptide_summary_id = '$peptide_summary_id'
  ~;
  my ($count) = $sbeams->selectOneColumn($sql);
  if ($count) {
    if ($delete_existing) {
      print "Deleting...\n$sql\n";
      $sql = "DELETE FROM $TBAPD_PEPTIDE ".
             " WHERE peptide_summary_id = '$peptide_summary_id'";
      $sbeams->executeSQL($sql);
    } elsif (!($update_existing)) {
      die("There are already peptide records for this " .
        "peptide_summary.\nPlease delete those records before trying to " .
        "load new peptides,\nor specify the --delete_existing ".
        "or --update_existing flags.");
    }
  }


  #### Obtain some properties about this peptide_summary
  my $status = getPeptideSummaryStatus(
    peptide_summary_id => $peptide_summary_id);
  my $minimum_probability = $status->{minimum_probability};
  my $experiment_list = $status->{experiment_list};

print "minimum_probability = ",$minimum_probability,"\n";
print "experiment_list = ",$experiment_list,"\n";

  #### Define main query to get data to fill tables with
  $sql = qq~
	SELECT
           S.file_root AS 'file_root',
           STR(MSS.calc_buffer_percent,7,1) AS 'calc_buffer_percent',
           best_hit_flag AS 'best_hit_flag',
           STR(SH.probability,7,3) AS 'probability',
           LTRIM(STR((S.sample_mass_plus_H+(S.assumed_charge-1)*1.008)/S.assumed_charge,7,2)) AS 'precursor_mass',
           CONVERT(varchar(20),SH.hit_mass_plus_H) + ' (' + STR(SH.mass_delta,5,2) + ')' AS 'hit_mass_plus_H',
           STR(SH.identified_ions,2,0) + '/' + STR(SH.total_ions,3,0) AS 'ions',
           reference AS 'reference',
           additional_proteins AS 'additional_proteins',
           peptide_string AS 'peptide_string',
           STR(isoelectric_point,8,3) AS 'isoelectric_point',
           peptide AS 'peptide',
           SH.biosequence_id AS 'biosequence_id',
           S.assumed_charge AS 'assumed_charge',
           AL.annotation_probability AS 'annotation_probability'
	  FROM proteomics.dbo.search_hit SH
	  JOIN proteomics.dbo.search S ON ( SH.search_id = S.search_id )
	  JOIN proteomics.dbo.search_batch SB ON ( S.search_batch_id = SB.search_batch_id )
	  JOIN proteomics.dbo.msms_spectrum MSS ON ( S.msms_spectrum_id = MSS.msms_spectrum_id )
	  JOIN proteomics.dbo.fraction F ON ( MSS.fraction_id = F.fraction_id )
	  JOIN proteomics.dbo.biosequence_set BSS ON ( SB.biosequence_set_id = BSS.biosequence_set_id )
	  JOIN proteomics.dbo.proteomics_experiment PE ON ( F.experiment_id = PE.experiment_id )
	  LEFT JOIN proteomics.dbo.quantitation QUAN ON ( SH.search_hit_id = QUAN.search_hit_id )
	  LEFT JOIN proteomics.dbo.biosequence BS ON ( SB.biosequence_set_id = BS.biosequence_set_id AND SH.reference = BS.biosequence_name )
	  LEFT JOIN proteomics.dbo.search_hit_annotation SHA ON ( SH.search_hit_id = SHA.search_hit_id )
	  LEFT JOIN proteomics.dbo.annotation_label AL ON ( SHA.annotation_label_id = AL.annotation_label_id )
	 WHERE 1 = 1
	   AND SB.search_batch_id IN ( $experiment_list )
	   AND ( ( SH.probability >= '$minimum_probability'
	           AND ( SHA.annotation_label_id IN ( 1 ) OR SHA.annotation_label_id IS NULL ) )
                 OR SHA.annotation_label_id IN ( 1 )
               )
	 ORDER BY peptide,peptide_string,assumed_charge,S.file_root,experiment_tag,set_tag,SH.cross_corr_rank,SH.hit_index
  ~;

  #print "$sql\n\n" if ($VERBOSE);
  my @rows = $sbeams->selectSeveralColumns($sql);


  #### Definitions for loop
  my ($prev_peptide,$prev_peptide_string,$prev_charge)= ('','','');
  my ($peptide_data,$mod_peptide_data);
  my $counter = 0;
  my $row;


  #### Loop over all data in the file
  my $first_flag=1;
  foreach $row (@rows) {

   #### Extract data from the row
   my ($file_root,$calc_buffer_percent,$best_hit_flag,$probability,
       $precursor_mass,$hit_mass_plus_H,$ions,$reference,$additional_proteins,
       $peptide_string,$isoelectric_point,$peptide,$biosequence_id,
       $assumed_charge,$annotation_probability) = @{$row};


    #### If the human annotated probability is higher than the natural one,
    #### then substitute it
    $probability = $annotation_probability
      if (defined($annotation_probability) &&
          $annotation_probability > $probability);


    #### If this is a new peptide, write out the previous and set up the new
    if ($peptide ne $prev_peptide) {

      unless ($first_flag) {
        print "Writing peptide information.\n\n" if ($VERBOSE);

        push(@{$peptide_data->{modified_peptides}},$mod_peptide_data);
        $first_flag = 1;

        writePeptide(peptide_data=>$peptide_data);
      }

      my %tmphash = ();
      $peptide_data = \%tmphash;

      $peptide_data->{peptide_summary_id} = $peptide_summary_id;
      $peptide_data->{biosequence_id} = $biosequence_id;
      $peptide_data->{biosequence_name} = $reference;
      $peptide_data->{peptide} = $peptide;
      $peptide_data->{n_peptides} = 0;
      $peptide_data->{maximum_probability} = 0.0;

      my @modified_peptides = ( );
      $peptide_data->{modified_peptides} = \@modified_peptides;

      print "New peptide $peptide\n" if ($VERBOSE);

    }


    #### Update the peptide properties
    $peptide_data->{n_peptides}++;
    $peptide_data->{maximum_probability} = $probability
      if ($peptide_data->{maximum_probability} < $probability);


    #### If this is exactly the same as the previous one, update stats
    if ($peptide_string eq $prev_peptide_string and
        $assumed_charge eq $prev_charge) {

      $mod_peptide_data->{n_modified_peptides}++;

      #### Just add the additional stats that we keep track of
      push(@{$mod_peptide_data->{precursor_masses}},$precursor_mass);
      push(@{$mod_peptide_data->{probabilities}},$probability);

      print "    Another $peptide_string, ".
        "charge = $assumed_charge\n" if ($VERBOSE);


    #### Otherwise, store the final stats and start new ones
    } else {

      #### Store the data from the previous modified peptide
      unless ($first_flag) {
        push(@{$peptide_data->{modified_peptides}},$mod_peptide_data);
      }

      #### Create a new structure for the new modified peptide
      my %tmphash = ();
      $mod_peptide_data = \%tmphash;

      $mod_peptide_data->{peptide_string} = $peptide_string;
      $mod_peptide_data->{charge_state} = $assumed_charge;
      $mod_peptide_data->{n_modified_peptides} = 1;

      my @precursor_masses = ( $precursor_mass );
      $mod_peptide_data->{precursor_masses} = \@precursor_masses;

      my @probabilities = ( $probability );
      $mod_peptide_data->{probabilities} = \@probabilities;

      print "  New peptide_string $peptide_string, ".
        "charge = $assumed_charge\n" if ($VERBOSE);

    }


    #### Set the previous entity information
    $prev_peptide = $peptide;
    $prev_peptide_string = $peptide_string;
    $prev_charge = $assumed_charge;
    $first_flag = 0;


    #### Print some progress information
    #last if ($counter > 5);
    $counter++;
    print "$counter..." if ($counter % 100 == 0);


  }


  print "\n$counter rows processesed\n";

}


###############################################################################
# writePeptide
###############################################################################
sub writePeptide {
  my %args = @_;
  my $SUB_NAME = 'writePeptide';


  #### Decode the argument list
  my $peptide_data = $args{'peptide_data'}
   || die "ERROR[$SUB_NAME]: peptide_data not passed";


  #### Define standard variables
  my ($i,$element,$key,$value,$line,$result,$sql);


  #### Print out the data structure if very verbose
  print Dumper($peptide_data) if ($VERBOSE > 1);


  #### Shortcut stuff skipping UPDATE functionality
  my $insert = 1;
  my $update = 0;
  my $peptide_id = 0;


  #### Create a hash for the peptide row
  my %rowdata;
  $rowdata{peptide_summary_id} = $peptide_data->{peptide_summary_id};
  $rowdata{biosequence_id} = $peptide_data->{biosequence_id};
  $rowdata{biosequence_name} = $peptide_data->{biosequence_name};
  $rowdata{peptide} = $peptide_data->{peptide};
  $rowdata{n_peptides} = $peptide_data->{n_peptides};
  $rowdata{maximum_probability} = $peptide_data->{maximum_probability};


  #### Insert the data into the database
  $peptide_id = $sbeams->insert_update_row(
    insert=>$insert,
    update=>$update,
    table_name=>"$TBAPD_PEPTIDE",
    rowdata_ref=>\%rowdata,
    PK=>"peptide_id",
    PK_value => $peptide_id,
    return_PK => 1,
    verbose=>$VERBOSE,
    testonly=>$TESTONLY,
  );


  unless ($peptide_id > 0) {
    die("Unable to insert peptide");
  }


  #### Write out all the modified peptide instances
  foreach my $modified_peptide (@{$peptide_data->{modified_peptides}}) {

    #### Add peptide_id information
    $modified_peptide->{peptide_id} = $peptide_id;

    writeModifiedPeptide(
      modified_peptide_data => $modified_peptide,
    );

  }


  print "\n\n";

}


###############################################################################
# writeModifiedPeptide
###############################################################################
sub writeModifiedPeptide {
  my %args = @_;
  my $SUB_NAME = 'writeModifiedPeptide';


  #### Decode the argument list
  my $modified_peptide_data = $args{'modified_peptide_data'}
   || die "ERROR[$SUB_NAME]: modified_peptide_data not passed";


  #### Define standard variables
  my ($i,$element,$key,$value,$line,$result,$sql);


  #### Print out the data structure if very verbose
  print Dumper($modified_peptide_data) if ($VERBOSE > 1);


  #### Shortcut stuff skipping UPDATE functionality
  my $insert = 1;
  my $update = 0;
  my $modified_peptide_id = 0;


  #### Create a hash for the peptide row
  my %rowdata;
  $rowdata{peptide_id} = $modified_peptide_data->{peptide_id};
  $rowdata{peptide_string} = $modified_peptide_data->{peptide_string};
  $rowdata{charge_state} = $modified_peptide_data->{charge_state};
  $rowdata{n_modified_peptides} =
    $modified_peptide_data->{n_modified_peptides};


  #### Calculate statistics for various items
  my $prob_stats = calculateMoment(
    array_ref=>$modified_peptide_data->{probabilities});
  $rowdata{maximum_probability} = $prob_stats->{max};

  my $mass_stats = calculateMoment(
    array_ref=>$modified_peptide_data->{precursor_masses});
  $rowdata{avg_precursor_mass} = $mass_stats->{mean};


  #### Insert the data into the database
  $modified_peptide_id = $sbeams->insert_update_row(
    insert=>$insert,
    update=>$update,
    table_name=>"$TBAPD_MODIFIED_PEPTIDE",
    rowdata_ref=>\%rowdata,
    PK=>"peptide_id",
    PK_value => $modified_peptide_id,
    return_PK => 1,
    verbose=>$VERBOSE,
    testonly=>$TESTONLY,
  );


  unless ($modified_peptide_id > 0) {
    die("Unable to insert modified_peptide");
  }


}


###############################################################################
# calculateMoment
###############################################################################
sub calculateMoment {
  my %args = @_;
  my $SUB_NAME = 'calculateMoment';


  #### Decode the argument list
  my $array_ref = $args{'array_ref'}
   || die "ERROR[$SUB_NAME]: array_ref not passed";


  #### Define standard variables
  my ($i,$element,$key,$value,$line,$result,$sql);


  #### Set up some things to calculate
  my $min = $array_ref->[0];
  my $max = $array_ref->[0];
  my $mean = 0.0;
  my $n_elements = scalar(@{$array_ref});


  #### Loop through the array, obtaining stats
  foreach $element (@{$array_ref}) {
    $min = $element if ($element < $min);
    $max = $element if ($element > $max);
    $mean += $element;
  }


  #### Finish a few calculations
  $mean = $mean / $n_elements;


  #### Create a final hash of results and return a reference to it
  my %results;
  $results{min} = $min;
  $results{max} = $max;
  $results{mean} = $mean;
  $results{n_elements} = $n_elements;

  return \%results;

}


