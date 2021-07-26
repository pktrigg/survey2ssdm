#name:			ssdmfieldvalue.txt
#created:		August 2019
#by:			paul.kennedy@guardiangeomatics.com
#description:   This file contains a list of the static SSDM values which would be applied to an SSDM GIS database on a per-project basis.  
#The concept is the user edits the file once, and then each and every layer of data has fields populated by the tools which create those layers.

###SSDMOBJECT fields...
#survey_id needs to be an INTEGER number
SURVEY_ID,1006
SURVEY_ID_REF,Great North East Passage
REMARKS, None

###Proposed_Survey_Run_Lines fields
SURVEY_NAME,SI1006
LINE_PREFIX,MBES
PROJECT_NAME,Great North East Passage
SURVEY_BLOCK_NAME,surveyblockname
LAYER,proposedlines
APPROVED_BY,Paul Kennedy


###Survey_TrackLines fields
CONTRACTOR_NAME, Guardian Geomatics
TRACK_SYMBOLOGY_CODE, TRACK_SYMBOLOGY_CODE
TRACK_LAYER, TRACK_LAYER

DATA_URL, dataurl
REPORT_URL, reporturl

#TSdip_Sample_Pnt
INSTRUMENT_USED, Valeport MiniSVP

###SEARCH FOLDERS
#you can refine the search for input files such as raw MBES, SVP etc by configuring the folders here.  these names will be appended to the '-i inputfolder' name, so please onyl specify the relative folder rather than the absolute folder. if you leave this blank, it will search all subfolders from the main folder
MBES_RAW_FOLDER, 
MBES_RAW_FILENAME, *.kmall
