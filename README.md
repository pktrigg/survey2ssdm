# survey2ssdm
import a hydrographic survey to an opensource geopackage using the SSDM 2.0 schema

######################
#done
# added option to create a per ping navigation file which we can import into caris.  we needed this due to a potential bug in caris importing kmall files.
# -config to open the ssdm field names so users can edit
# create proposed survey lines from KML files as exported from qinsy
# record what is done to a log and skip files already processed
# multi process for performance gains when dealing with thousands of files.
# release on github
# create track plots from kmall files
# create track plots from RESON 7k files
# create track plots from KMraw files
# create track plots from EIVA SBD files
# create track plots from SEGY files.

######################
#2do
# complete SSDM creation to create all tables within SSDM V2
# test routine to create a full set of empty tables
# write up notes on an opensource geopackage implementaion of SSDM 

# create tsdip from SVP files.  for this we need the coordinates of the vessel.  we can get this from the SSDM survey track POINT FC if we read it back
# create track coverage from kmall files
# create track points with timestamps so we can spatially georeference SVP data


######################
#Notes
# DELPH INS Navigation export
#
# date: Date of validity (yyyy/mm/dd)
# time: Time of validity (hh:mm:ss.ssss)
# latitude: Latitude, decimal degree
# longitude: Longitude, decimal degree
# ellipsoidHeight: Height, meter positive upward
# heading: Heading, degree
# roll: Roll, degree
# pitch: Pitch, degree
# heave: Heave, meter positive upward
#
#date	time	latitude	longitude	ellipsoidHeight	heading	roll	pitch	heave

