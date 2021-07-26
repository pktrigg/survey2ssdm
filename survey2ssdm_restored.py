#name:			survey2ssdm.py
#created:		Jan 2019
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to scan a folder structure and import various supported file formats and convert to a SSDM schema within the OGC SSDM schema
######################
#done
# -config to open the ssdm field names so users can edit
# create proposed survey lines from KML files as exported from qinsy
# record what is done to a log and skip files already processed
# multi process for performance gains when dealing with thousands of files.
# release on github
# create track plots from kmall files

######################
#2do
# clear out exiting table and replace with new table
# complete SSDM creation to create all tables within SSDM V2
# test routine to create a full set of empty tables
# write up notes on an opensource geopackage implementaion of SSDM 
# create track plots from s7k files
# create tsdip from SVP files.  for this we need the coordinates of the vessel.  we can get this from the SSDM survey track POINT FC if we read it back
# create track coverage from kmall files
# create track points with timestamps so we can spatially georeference SVP data



import sys
import time
import os
import tempfile
import ctypes
import fnmatch
import math
import json
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
from datetime import datetime
from datetime import timedelta
from glob import glob
import uuid
import multiprocessing as mp
import pyproj

import readkml
# local from the shared area...
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
import fileutils
import geodetic
# import SSDM
import geopackage
import geopackage_ssdm
# import huginbinreader
# import position_smoothreader
# import topsideauvpos_reader
# import navdata
# import timeseries
# import navpos_reader
# import depthreader
# import mpio
# import vehiclectdreader
import ssdmfieldvalue
# import pyall
# import all2coverage
import kmall
import pys7k

import multiprocesshelper

# we need to do this as airflow and regular python cmdline interpreter differ.
# localpath = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(localpath)


##############################################################################
def main():

	parser = ArgumentParser(description='Read any Survey folder and create a OGC compliant GEOPackage in the SSDM Schema summarising the survey. This is a distillation process extracting important spatial attributes from the survey in an automated and rigorous manner.',
			epilog='Example: \n To process all files under a root folder use -i c:/foldername \n', formatter_class=RawTextHelpFormatter)
	parser.add_argument('-i', 		action='store', 		default="",		dest='inputfolder', 	help='input folder to process.')
	parser.add_argument('-o', 		action='store', 		default="",		dest='outputFilename', 	help='output GEOPACKAGE filename.')
	parser.add_argument('-s', 		action='store', 		default="1",	dest='step', 			help='decimate the data to reduce the output size. [Default: 1]')
	parser.add_argument('-odir', 	action='store', 		default="",	dest='odir', 			help='Specify a relative output folder e.g. -odir GIS')
	parser.add_argument('-config', 	action='store_true', 	default=False,	dest='config', 			help='Open the SSDM configuration file for editing e.g. -config')
	parser.add_argument('-opath', 	action='store', 		default="",	dest='opath', 			help='Specify an output path e.g. -opath c:/temp')
	parser.add_argument('-odix', 	action='store', 		default="",	dest='odix', 			help='Specify an output filename appendage e.g. -odix _coverage')
	parser.add_argument('-epsg', 	action='store', 		default="4326",	dest='epsg', 			help='Specify an output EPSG code for transforming from WGS84 to East,North,e.g. -epsg 4326')
	parser.add_argument('-all', 	action='store_true', 	default=True, 	dest='all', 			help='extract all supported forms of data (ie do everything).')
	parser.add_argument('-reprocess', 	action='store_true', 	default=False, 	dest='reprocess', 			help='reprocess the survey folders by re-reading input files and creating new GIS features, ignoring the cache files. (ie do everything).')
	parser.add_argument('-cpu', 		dest='cpu', 			action='store', 		default='0', 	help='number of cpu processes to use in parallel. [Default: 0, all cpu]')
	# parser.add_argument('-auv', 	action='store_true', 	default=False, 	dest='auv', 			help='extract the REALTIME AUV positions as computed by the AUV.')
	# parser.add_argument('-navlab', 	action='store_true', 	default=False, 	dest='navlab', 			help='extract the PROCESSED NAVLAB.')
	# parser.add_argument('-hipap', 	action='store_true',	default=False, 	dest='hipap', 			help='extract the HIPAP UPDATES.')
	# parser.add_argument('-utp', 	action='store_true', 	default=False, 	dest='utp', 			help='extract the UTP position UPDATES.')
	# parser.add_argument('-mp', 		action='store_true', 	default=False, 	dest='mp', 				help='extract the survey plan.')
	# parser.add_argument('-vessel', 	action='store_true', 	default=False, 	dest='vessel', 			help='extract the vessel position UPDATES.')
	# parser.add_argument('-mbes', 	action='store_true', 	default=False, 	dest='mbes', 			help='extract the AUV Multibeam coverage polygon.')
	# parser.add_argument('-ctd', 	action='store_true', 	default=False, 	dest='ctd', 			help='extract the /env/ctd file.')
	# parser.add_argument('-qc', 		action='store_true', 	default=False, 	dest='qcreport', 		help='create a QC report of navigation quality.')


	args = parser.parse_args()
	# if len(sys.argv)==1:
	# 	parser.print_help()
	# 	sys.exit(1)

	if args.config:
		geopackage.openSSDMFieldValues()
		geopackage.openSSDMFieldValues()

	# user has not set any flags so do everything.  better than doing nothing.
	if args.all == False and \
		args.auv == False and \
		args.hipap == False and \
		args.navlab == False and \
		args.utp == False and \
		args.mp == False and \
		args.ctd == False and \
		args.mbes == False and \
		args.vessel == False:
			args.all = True

	if args.all:
		args.auv 			= True
		args.navlab			= True
		args.hipap 			= True
		args.utp 			= True
		args.qc 			= True
		args.mp 			= True
		args.ctd			= True
		args.vessel			= True
		args.mbes			= True

	if len(args.inputfolder) == 0:
		args.inputfolder = os.getcwd() + args.inputfolder

	if args.inputfolder == '.':
		args.inputfolder = os.getcwd() + args.inputfolder


	process(args)

###############################################################################
def process(args):
	if not os.path.isdir(args.inputfolder):
		print ("oops, input is not a folder.  Please specify a survey folder.")
		return

	surveyname = os.path.basename(args.inputfolder) #this folder should be the Survey NAME
	if args.opath == "":
		args.opath = os.path.join(args.inputfolder, "GIS")

	if len(args.outputFilename) == 0:
		args.outputFilename 	= os.path.join(args.opath, args.odir, surveyname + "_SSDM.gpkg")
		args.outputFilename  	= fileutils.addFileNameAppendage(args.outputFilename, args.odix)
		args.outputFilename 	= fileutils.createOutputFileName(args.outputFilename)
	
	# create the gpkg...
	gpkg = geopackage.geopackage(args.outputFilename, int(args.epsg))
	# pkpk this does not yet work...
	# gpkg.addEPSG(args.epsg)

	#load the python proj projection object library if the user has requested it
	geo = geodetic.geodesy(args.epsg)

	# processsurveyPlan(args, args.inputfolder, gpkg, geo)

	mp_processKMALL(args, gpkg, geo)


	# # # process the smooth positions from the /post folder.  This is the navlab post processed results.
	# if args.navlab:
	# 	nav = processNavlabBinaryResults(args, gpkg, geo)
	# 	if nav == None:
	# 		# there was no navlab file so we need to try read the navlab ascii files instead
	# 		nav = processNavlabASCIIResults(args, gpkg, geo)

	# # # process the UTP ranges from the DB folder and create range lines from the beacon to the AUV track so we can visualise.
	# if args.utp:
	# 	processUTP(args, gpkg, geo, nav)

	# # # process the REAL TIME strapdown navigator
	# if args.auv:
	# 	processStrapdown(args, gpkg, geo)

	# process the REAL TIME Hipap USBL updates as recorded by the AUV
	# if args.hipap:
	# 	processHipapUpdates(args, geo, gpkg)
	# 	processTopsideAUVPos(args, geo, gpkg)


	# # if args.ctd:
	# # 	processCTD(args, gpkg, geo, surveyname)

	# if args.vessel:
	# 	processTopsideVesselPos(args, geo, gpkg)

	# if args.mbes:
	# 	processMBESCoverage(args, geo, gpkg)

	print("Completed processing to file: %s" %(args.outputFilename))

###############################################################################
def findsurveys(args):
	'''high level funciton to recursively find all the surveys in all subfolders'''
	surveys = []
	#add the base folder as a candidate in case this is the folde rth euser specified.
	if folderisasurvey(args.inputfolder):
		surveys.append(args.inputfolder)
		return surveys
	#looks like the user has specificed a higher level folder such as a root drive or project folder so scan deeply	
	print("Scanning for surveys from root folder %s ...." % (args.inputfolder))
	folders = fast_scandir(args.inputfolder)
	for folder in folders:
		if folderisasurvey(folder):
			surveys.append(folder)
	print("surveys to Process: %s " % (len(surveys)))
	return surveys

###############################################################################
def folderisasurvey(dirname):
	'''validate if this is a real survey by testing if there is a survey.mp file in the folder '''
	# filename = os.path.join(dirname, "events.txt")
	# if not os.path.exists(filename):
	# 	return False

	surveys = fileutils.findFiles2(False, dirname, "*survey.mp")
	if len(surveys)==0:
	# filename = os.path.join(dirname, "survey.mp")
	# if not os.path.exists(filename):
		return False

	return True

###############################################################################
def fast_scandir(dirname):
	subfolders = []
	for root, dirs, files in os.walk(dirname, topdown=True):
		# for name in files:
		# 	print(os.path.join(root, name))
		if root in subfolders:
			continue
		for name in dirs:
			dirname = os.path.join(root, name)
			print (dirname)
			if folderisasurvey(dirname):
				subfolders.append(dirname)
				# dirs[:] = []
				sys.stdout.write('.')
				sys.stdout.flush()
	# subfolders = [x[0] for x in os.walk(dirname)]
	# subfolders= [f.path for f in os.scandir(dirname) if f.is_dir()]
	# if subfolders is not None:
	# 	for dirname in list(subfolders):
	# 		subfolders.extend(fast_scandir(dirname))
	# else:
	# 	print("oops")
	return subfolders
###############################################################################
def update_progress(job_title, progress):
	length = 20 # modify this to change the length
	block = int(round(length*progress))
	msg = "\r{0}: [{1}] {2}%".format(job_title, "#"*block + "-"*(length-block), round(progress*100, 2))
	if progress >= 1: msg += " DONE\r\n"
	sys.stdout.write(msg)
	sys.stdout.flush()

###############################################################################
# def processCTD(args, gpkg, geo, surveyname):
# 	'''import the survey.mp file into the geopackage'''
# 	filename = os.path.join(args.inputfolder, "env/ctd/" + "vehiclectd.txt")
# 	if not os.path.isfile(filename):	
# 		print ("survey CTD file not found, skipping %s" % (filename))
# 		return


# 	table = vectortable (connection, tablename, epsg, type, fields)
# 	return table

# 	#create the linestring table for the survey plan
# 	table = geopackage.createTSdip_Sample_Pnt(gpkg.connection, "TSdip_Sample_Pnt", gpkg.epsg)

# 	reader = vehiclectdreader.ctdreader(filename)
# 	createsurveyctd(reader, table, geo, surveyname)
	
# ###############################################################################
def processsurveyPlan(args, surveyfolder, gpkg, geo):
	'''import the survey.mp file into the geopackage'''
	matches = fileutils.findFiles(True, args.inputfolder, "*.kml")

	if len(matches) == 0:
		print("No KML files found for importing to survey line plan, skipping")
		return

	#create the linestring table for the survey plan
	type, fields = geopackage_ssdm.createProposed_Survey_Run_Lines()
	linestringtable = geopackage.vectortable(gpkg.connection, "surveyPlan", gpkg.epsg, type, fields)

	# table = vectortable (connection, tablename, epsg, type, fields)
	# return table

	for filename in matches:
		reader = readkml.reader(filename)
		print ("File: %s Survey lines found: %d" % (filename, len(reader.surveylines)))
		createsurveyplan(reader, linestringtable, geo)

	# ###############################################################################
# def processUTP(args, gpkg, geo, nav):
# 	'''process the UTP ranges from the DB folder and create range lines from the beacon to the AUV track so we can visualise.'''
# 	'''The UTP data does not contain the AUV position at time of observation so we need to load the strapdown files into a timeseries class first.'''
# 	''' we can then use time to determine where the AUV was located at UTP observation time.  We can then plot as a point just as we do for the HiPAP updates'''

# 	matches = fileutils.findFiles(True, args.inputfolder, "TpRangeData*.bin")
# 	surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

# 	if len(matches) == 0:
# 		print("No files found for UTP rendering, skipping")
# 		return

# 	#create the point table for the strapdown track points
# 	pointtable = geopackage.createUTPtable(gpkg.connection, "_UTP_UPDATES", "POINT", gpkg.epsg)
# 	linetable = geopackage.createUTPtable(gpkg.connection, "_UTP_RANGES", "LINESTRING", gpkg.epsg)

# 	UTPQCFileName = os.path.join(args.opath, args.odir,  surveyname + "_UTP_QC.csv")
# 	UTPQCFileName  = fileutils.addFileNameAppendage(UTPQCFileName, args.odix)
# 	UTPQCFileName = fileutils.createOutputFileName(UTPQCFileName)

# 	# load the strapdown realtime navigation into a timeseries...
# 	# nav = huginbinreader.huginrealtimenavigation(args.inputfolder)

# 	# load the NAVLAB processed navigation into a timeseries...
# 	# nav = navdata.huginnavlabnavigation(args.inputfolder)
	
# 	tslongitude, tslatitude, tsstandarddeviation = nav2timeseries(nav)

# 	for filename in matches:
# 		reader = huginbinreader.huginreader(filename)
# 		print("Processing UTP updates to point table:", filename)
# 		createTrackPointfromUTP(reader, pointtable, float(args.step), geo, tslongitude, tslatitude, tsstandarddeviation, UTPQCFileName, surveyname)
		
# 		print("Processing UTP Ranges:", filename)
# 		createRangeLinesFromUTP(reader, linetable, float(args.step), geo, tslongitude, tslatitude, tsstandarddeviation, surveyname)

# 	pointtable.close()
# 	linetable.close()

# ###############################################################################
# def nav2timeseries(nav):
# 	'''convert a list of nav updates into a time series so we can interpolate'''

# 	times = []
# 	longitudes = []
# 	latitudes = []
# 	standarddeviations = []

# 	for record in nav:
# 		times.append(record[0])
# 		longitudes.append(record[1])
# 		latitudes.append(record[2])
# 		standarddeviations.append(record[3])

# 	tslongitude = timeseries.cTimeSeries(times, longitudes)
# 	tslatitude = timeseries.cTimeSeries(times, latitudes)
# 	tsstandarddeviations = timeseries.cTimeSeries(times, standarddeviations)

# 	return tslongitude, tslatitude, tsstandarddeviations

################################################################################
def processKMALL(filename, outfilename, step):
	#now read the kmall file and return the navigation table filename

	# print("Loading Navigation...")
	r = kmall.kmallreader(filename)
	navigation = r.loadNavigation(step=1)
	r.close()

	with open(outfilename,'w') as f:
		json.dump(navigation, f)
	
	return(navigation)

################################################################################
def processS7k(filename, outfilename, step):
	#now read the s7k file and return the navigation table filename

	# print("Loading Navigation...")
	r = pys7k.s7kreader(filename)
	navigation = r.loadNavigation(step=1)
	r.close()

	with open(outfilename,'w') as f:
		json.dump(navigation, f)
	
	return(navigation)

################################################################################
def mp_processKMALL(args, gpkg, geo):

	# boundary = []
	boundarytasks = []
	results = []

	rawfolder = os.path.join(args.inputfolder, ssdmfieldvalue.readvalue("MBES_RAW_FOLDER"))
	if not os.path.isdir(rawfolder):
		rawfolder = args.inputfolder

	# rawfilename = ssdmfieldvalue.readvalue("MBES_RAW_FILENAME")


	# surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

	#create the linestring table for the trackplot
	type, fields = geopackage_ssdm.createSurveyTracklineSSDM()
	linestringtable = geopackage.vectortable(gpkg.connection, "SurveyTrackLine", args.epsg, type, fields)

	matches = fileutils.findFiles2(True, rawfolder, "*.kmall")
	for filename in matches:
		root = os.path.splitext(filename)[0]
		root = os.path.basename(filename)
		outputfolder = os.path.join(os.path.dirname(args.outputFilename), "log")
		os.makedirs(outputfolder, exist_ok=True)
		# makedirs(outputfolder)
		outfilename = os.path.join(outputfolder, root+"_navigation.txt").replace('\\','/')
		if args.reprocess:
			if os.path.exists(outfilename):
				os.unlink(outfilename)
		if os.path.exists(outfilename):
			# the cache file exists so load it
			with open(outfilename) as f:
				# print("loading file %s" %(outfilename))
				lst = json.load(f)
				results.append([filename, lst])
		else:
			boundarytasks.append([filename, outfilename])

	multiprocesshelper.log("New Files to Import: %d" %(len(boundarytasks)))		
	cpu = multiprocesshelper.getcpucount(args.cpu)
	multiprocesshelper.log("Extracting Navigation with %d CPU's" %(cpu))
	pool = mp.Pool(cpu)
	multiprocesshelper.g_procprogress.setmaximum(len(boundarytasks))
	# poolresults = [pool.apply_async(processKMALL, (task[0], task[1], args.step)) for task in boundarytasks]
	poolresults = [pool.apply_async(processKMALL, (task[0], task[1], args.step), callback=multiprocesshelper.mpresult) for task in boundarytasks]
	pool.close()
	pool.join()
	for idx, result in enumerate (poolresults):
		results.append([boundarytasks[idx][0], result._value])
		# print (result._value)


	# process the s7k...
	matches = fileutils.findFiles2(True, rawfolder, "*.s7k")
	for filename in matches:
		root = os.path.splitext(filename)[0]
		root = os.path.basename(filename)
		outputfolder = os.path.join(os.path.dirname(args.outputFilename), "log")
		os.makedirs(outputfolder, exist_ok=True)
		# makedirs(outputfolder)
		outfilename = os.path.join(outputfolder, root+"_navigation.txt").replace('\\','/')
		if args.reprocess:
			if os.path.exists(outfilename):
				os.unlink(outfilename)
		if os.path.exists(outfilename):
			# the cache file exists so load it
			with open(outfilename) as f:
				# print("loading file %s" %(outfilename))
				lst = json.load(f)
				results.append([filename, lst])
		else:
			boundarytasks.append([filename, outfilename])

	multiprocesshelper.log("New Files to Import: %d" %(len(boundarytasks)))		
	cpu = multiprocesshelper.getcpucount(args.cpu)
	multiprocesshelper.log("Extracting Navigation with %d CPU's" %(cpu))
	pool = mp.Pool(cpu)
	multiprocesshelper.g_procprogress.setmaximum(len(boundarytasks))
	# poolresults = [pool.apply_async(processs, (task[0], task[1], args.step)) for task in boundarytasks]
	poolresults = [pool.apply_async(processS7k, (task[0], task[1], args.step), callback=multiprocesshelper.mpresult) for task in boundarytasks]
	pool.close()
	pool.join()
	for idx, result in enumerate (poolresults):
		results.append([boundarytasks[idx][0], result._value])
		# print (result._value)


	# now we can read the results files and create the geometry into the SSDM table
	multiprocesshelper.log("Files to Import to geopackage: %d" %(len(results)))		

	multiprocesshelper.g_procprogress.setmaximum(len(results))
	for result in results:
		createTrackLine(result[0], result[1], linestringtable, float(args.step), geo)
		multiprocesshelper.mpresult("")

	# 	polygondetails2 = ds.getpolgonareas(result)
	# 	for idx, p  in enumerate(polygondetails2):
	# 		p.name = os.path.basename(result).replace("_coverage.shp", "")
	# 		boundary = boundary + [p]


	# for filename in matches:
	# 	reader = kmall.kmallreader(filename)

	# #create the point table for the strapdown track points
	# pointtable = geopackage.createPointSSDMGv2(gpkg.connection, "SurveyTrackPoint_NAVLAB", gpkg.epsg)
	# linestringtable = geopackage.createSurveyTracklineSSDMG(gpkg.connection, "SurveyTrackLine_NAVLAB", gpkg.epsg)
	
	# load the USBL observations into a timeseries so we can attribute the navlab trackplots with the age of the USBL...
	# usbl = huginbinreader.huginUSBLupdates(args.inputfolder)
	# usbl.loadUSBL()
	# # now make a time series of the USBL observations so we can find the nearest time and compute the age of last observation.
	# obs = []
	# for r in usbl.records:
	# 	obs.append([r.timestamp, r.standarddeviation])
	# usblobservations = timeseries.cTimeSeries(obs)

	# reader = navdata.NAVDATAReader(filename)
	# print("Processing NAVLAB Track point:", filename)
	# nav = reader.loadnavigation(float(args.step))
	# createTrackPoint(reader, nav, pointtable, float(args.step), geo, surveyname, usblobservations)

	# print("Processing NAVLAB Track line:", filename)
	# createTrackLine(reader, nav, linestringtable, float(args.step), geo, surveyname)

	# return nav

###############################################################################
def createTrackLine(filename, navigation, linestringtable, step, geo, surveyname=""):
	lastTimeStamp = 0
	linestring = []

	timeIDX				= 0
	longitudeIDX		= 1
	latitudeIDX			= 2
	depthIDX 			= 3
	headingIDX 			= 4
	rollIDX 			= 5
	pitchIDX 			= 6

	# navigation = reader.loadnavigation(step)
	totalDistanceRun = 0

	if navigation is None: #trap out empty files.
		return
	if len(navigation) == 0: #trap out empty files.
		print("file is empty: %s" % (filename))
		return

	prevX =  navigation[0][longitudeIDX]
	prevY = navigation[0][latitudeIDX]

	for update in navigation:
		distance = geodetic.est_dist(update[latitudeIDX], update[longitudeIDX], prevY, prevX)
		totalDistanceRun += distance
		prevX = update[longitudeIDX]
		prevY = update[latitudeIDX]

	# compute the brg1 line heading
	# distance, brg1, brg2 = geodetic.calculateRangeBearingFromGeographicals(navigation[0][1], navigation[0][2], navigation[-1][1], navigation[-1][2])
	# create the trackline shape file
	for update in navigation:
		if update[0] - lastTimeStamp >= step:
			x,y = geo.convertToGrid(update[longitudeIDX],update[latitudeIDX])
			linestring.append(x)
			linestring.append(y)
			lastTimeStamp = update[0]
	# now add the very last update
	x,y = geo.convertToGrid(float(navigation[-1][longitudeIDX]),float(navigation[-1][latitudeIDX]))
	linestring.append(x)
	linestring.append(y)
	# print("Points added to track: %d" % (len(line)))
	# now add to the table.
	recDate = from_timestamp(navigation[0][timeIDX]).strftime("%Y%m%d")
	
	###########################
	# write out the FIELDS data
	###########################

	# write out the FIELDS data
	fielddata = []
	fielddata += setssdmarchivefields() # 2 fields
	fielddata += setssdmobjectfields() # 4 fields

	# preparedDate = datetime.now()
	# userName = os.getenv('username')
	# filename = os.path.basename(filename)

	# fielddata = []
	# fielddata.append(datetime.now().date())
	# fielddata.append(os.getenv('username'))
	# fielddata.append(recDate)
	# fielddata.append(userName)

	fielddata.append(ssdmfieldvalue.readvalue("LINE_ID"))
	#LINE_NAME
	fielddata.append(os.path.basename(filename))
	#LAST_SEIS_PT_ID
	fielddata.append(int(navigation[-1][timeIDX]))
	#SYMBOLOGY_CODE
	fielddata.append(ssdmfieldvalue.readvalue("TRACK_SYMBOLOGY_CODE"))
	#DATA_SOURCE
	fielddata.append(os.path.basename(filename))
	#CONTRACTOR_NAME
	fielddata.append(ssdmfieldvalue.readvalue("CONTRACTOR_NAME"))
	#LINE_LENGTH
	fielddata.append(totalDistanceRun)
	#FIRST_SEIS_PT_ID
	fielddata.append(int(navigation[0][timeIDX]))
	#HIRES_SEISMIC_EQL_URL
	fielddata.append(ssdmfieldvalue.readvalue("HIRES_SEISMIC_EQL_URL"))
	#OTHER_DATA_URL
	fielddata.append(ssdmfieldvalue.readvalue("OTHER_DATA_URL"))
	#HIRES_SEISMIC_RAP_URL
	fielddata.append(ssdmfieldvalue.readvalue("HIRES_SEISMIC_RAP_URL"))
	#LAYER
	fielddata.append(ssdmfieldvalue.readvalue("TRACK_LAYER"))
	#SHAPE_Length
	fielddata.append(totalDistanceRun)


	# fielddata.append(0)
	# fielddata.append(datetime.now().date())
	# fielddata.append(os.getenv('username'))
	# fielddata.append(datetime.now().date())

	# fielddata.append(totalDistanceRun)
		
	# now write the point to the table.
	linestringtable.addlinestringrecord(linestring, fielddata)		
	linestringtable.close()

	#########################################################################################
	# qcreportFileName = os.path.join(args.opath, args.odir, surveyname + "QCReport.csv")
	# qcreportFileName  = fileutils.addFileNameAppendage(qcreportFileName, args.odix)
	# qcreportFilename = fileutils.createOutputFileName(qcreportFileName)

	# print("Processing Track line:", filename)
	# totalDistanceRun = createTrackLine(reader, TLshp, float(args.step), geo, surveyname)
		# if args.qcreport:
		# 	hts = timeseries.cTimeSeries([[0,0]])
		# 	vts = timeseries.cTimeSeries([[0,0]])
		# 	ats = timeseries.cTimeSeries([[0,0]])
		# 	# load the realtime positions so we can get hold of the real time standard deviations...
		# 	matches = fileutils.findFiles2(True, args.inputfolder + "/cp/data/", "navpos.txt")
		# 	for filename in matches:
		# 		navpos = navpos_reader.navposreader(filename)
		# 		hts, vts = navpos.loadstdevtimeseries()

		# 	# load the altitudes so we can write them into the QC report...
		# 	matches = fileutils.findFiles2(True, args.inputfolder + "/cp/data/", "depth.txt")
		# 	for filename in matches:
		# 		depth = depthreader.depthreader(filename)
		# 		ats = depth.loadaltitudetimeseries()

		# 	print("Processing QCReport:", qcreportFilename)
		# 	createQCReportfromNavlab(reader, float(args.step), hts, vts, ats, surveyname, qcreportFilename)


# # ###############################################################################
# def processNavlabASCIIResults(args, gpkg, geo):

# 	# if its a file, handle it nicely.
# 	surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

# 	filename = os.path.join(args.inputfolder, "POST", "position_smooth.txt")
# 	if not os.path.isfile(filename):	
# 		print ("file not found, skipping %s" % (filename))
# 		return None

# 	#create the point table for the strapdown track points
# 	pointtable = geopackage.createPointSSDMGv2(gpkg.connection, "SurveyTrackPoint_NAVLAB", gpkg.epsg)
# 	#create the linestring table for the strapdown trackplot
# 	linestringtable = geopackage.createSurveyTracklineSSDMG(gpkg.connection, "SurveyTrackLine_NAVLAB", gpkg.epsg)

# 	# load the USBL observations into a timeseries so we can attribute the navlab trackplots with the age of the USBL...
# 	usbl = huginbinreader.huginUSBLupdates(args.inputfolder)
# 	usbl.loadUSBL()
# 	# now make a time series of the USBL observations so we can find the nearest time and compute the age of last observation.
# 	obs = []
# 	for r in usbl.records:
# 		obs.append([r.timestamp, r.standarddeviation])
# 	usblobservations = timeseries.cTimeSeries(obs)

# 	reader = position_smoothreader.positionreader(filename)
# 	print("Processing NAVLAB Track point:", filename)
# 	nav = reader.loadnavigation(float(args.step))
# 	createTrackPoint(reader, nav, pointtable, float(args.step), geo, surveyname, usblobservations)

# 	print("Processing NAVLAB Track line:", filename)
# 	createTrackLine(reader, nav, linestringtable, float(args.step), geo, surveyname)

# 	return nav

# # ###############################################################################
# def processHipapUpdates(args, geo, gpkg):
# 	'''convert the hipap updates to a shapefile so we can better visualise the data qualilty and coverage'''
# 	matches = fileutils.findFiles2(True, args.inputfolder, "DGPSHiPAPData*.bin")
# 	surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

# 	#create the point table for the strapdown track points
# 	pointtable = geopackage.createPointSSDMGv2(gpkg.connection, "SurveyTrackPoint_HIPAP_Updates", gpkg.epsg)

# 	for filename in matches:
# 		reader = huginbinreader.huginreader(filename)
# 		print("Processing HIPAP updates:", filename)
# 		nav = reader.loadnavigation(float(args.step))
# 		createTrackPoint(reader, nav, pointtable, float(args.step), geo, surveyname)

# # ###############################################################################
# def processTopsideAUVPos(args, geo, gpkg):
# 	'''convert the TopsideAUVPos.txt so we can better visualise the data qualilty and coverage'''
# 	filename = os.path.join(args.inputfolder, "TopsideAUVPos.txt")
# 	surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

# 	#create the point table for the strapdown track points
# 	pointtable = geopackage.createPointSSDMGv2(gpkg.connection, "SurveyTrackPoint_TopsideAUVPos_Updates", gpkg.epsg)

# 	reader = topsideauvpos_reader.posreader(filename)
# 	print("Processing TopsideAUVPos(AUV positions):", filename)
# 	nav = reader.loadnavigation()
# 	createTrackPoint(reader, nav, pointtable, float(args.step), geo, surveyname)

# 	# ###############################################################################
# def processTopsideVesselPos(args, geo, gpkg):
# 	'''convert the TopsideAUVPos.txt so we can better visualise the data qualilty and coverage'''
# 	filename = os.path.join(args.inputfolder, "TopsideAUVPos.txt")
# 	surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

# 	#create the point table for the strapdown track points
# 	pointtable = geopackage.createPointSSDMGv2(gpkg.connection, "SurveyTrackPoint_TopsideVesselPos_Updates", gpkg.epsg)

# 	reader = topsideauvpos_reader.posreader(filename)
# 	print("Processing TopsideAUVPos(Vessel positions):", filename)
# 	loadvessel = True
# 	nav = reader.loadnavigation(float(args.step), loadvessel)
# 	createTrackPoint(reader, nav, pointtable, float(args.step), geo, surveyname)

# 	# now draw a line between the AUV and the vessel so we can better understand that conneciton.  This helps when analysing the position quality
# 	#create the linestring table for the vessel (mothership) track
# 	tracktable = geopackage.createSurveyTracklineSSDMG(gpkg.connection, "SurveyTrackLine_TopsideVesselPos_Updates", gpkg.epsg)

# 	# make the track line for the VESSEL
# 	createTrackLine(reader, nav, tracktable, float(args.step), geo, surveyname)

# ################################################################################
# def processMBESCoverage(args, geo, gpkg):
# 	'''convert the TopsideAUVPos.txt so we can better visualise the data qualilty and coverage'''
# 	matches = fileutils.findFiles2(True, args.inputfolder, "pp/em2040/*.all")
# 	surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

# 	# now draw a line between the AUV and the vessel so we can better understand that conneciton.  This helps when analysing the position quality
# 	#create the linestring table for the vessel (mothership) track
# 	table = geopackage.createCoverageSSDMG(gpkg.connection, "MBESCoverage", gpkg.epsg)

# 	for filename in matches:
# 		reader = pyall.ALLReader(filename)
# 		print("Processing MBES Coverage:", filename)

# 		# make the coverage polygon for the MBES
# 		creatembescoverage(reader, table, float(args.step), geo, surveyname)

# ###############################################################################
# def processStrapdown(args, gpkg, geo):

# 	matches = fileutils.findFiles2(True, args.inputfolder, "strapdown*.bin")
# 	surveyname = os.path.basename(args.inputfolder) #this folder should be the survey NAME

# 	#create the point table for the strapdown track points
# 	pointtable = geopackage.createPointSSDMGv2(gpkg.connection, "SurveyTrackPoint_REALTIME", gpkg.epsg)
# 	#create the linestring table for the strapdown trackplot
# 	linestringtable = geopackage.createSurveyTracklineSSDMG(gpkg.connection, "SurveyTrackLine_REALTIME", gpkg.epsg)
	
# 	for filename in matches:
# 		reader = huginbinreader.huginreader(filename)
# 		print("Processing Track point:", filename)
# 		nav = reader.loadnavigation(float(args.step))
# 		createTrackPoint(reader, nav, pointtable, float(args.step), geo, surveyname)

# 		print("Processing Track line:", filename)
# 		createTrackLine(reader, nav, linestringtable, float(args.step), geo, surveyname)
# 		# 	# print ("%s Trackplot Length: %.3f" % (filename, totalDistanceRun))


# ###############################################################################
# def createQCReportfromNavlab(reader, step, hts, vts, ats, surveyname="testsurvey", qcreportFilename = "c:/temp/qcreport.txt"):
# 	lastTimeStamp 		= 0
# 	thu					= 0
# 	tvu 				= 0
# 	thuaccepted			= 0
# 	tvuaccepted			= 0
# 	altitude 			= 0

# 	# open the survey for append.
# 	print("writing report to: %s" % (qcreportFilename))
# 	if os.path.isfile(qcreportFilename):
# 		reportptr = open(qcreportFilename, 'a')
# 	else:
# 		reportptr = open(qcreportFilename, 'w')
# 		reportptr.write("time, longitude, latitude, depth, roll, pitch, heading, altitude, RTstdDevPos, RTstdDevDepth, stdDevPos,stdDevDepth, thuthreshold, tvuthreshold, thuaccepted, tvuaccepted\n")

# 	reader.rewind() #rewind to the start of the file
# 	while reader.moreData() > 0:
# 		reader.readDatagram()
# 		if reader.timestamp - lastTimeStamp > step:
# 			# compute the client threshold for THU and TPU
# 			thu, tvu = computepetrobrastvu(reader.depth)
# 			if reader.stdDevPos <= thu:
# 				thuaccepted = 1
# 			else:
# 				thuaccepted = 0
# 			if reader.stdDevDep <= thu:
# 				tvuaccepted = 1
# 			else:
# 				tvuaccepted = 0

# 			RTstdDevPos = hts.getValueAt(reader.timestamp)
# 			RTstdDevDepth = vts.getValueAt(reader.timestamp)
# 			altitude = ats.getValueAt(reader.timestamp)
# 			thu, tvu = computepetrobrastvu(abs(reader.depth))
# 			reportptr.write("%s,%.8f,%.8f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%d,%d\n" % (from_timestamp(reader.timestamp).strftime("%Y/%m/%d %H:%M:%S"),reader.longitude,reader.latitude, reader.depth, reader.roll, reader.pitch, reader.heading, altitude, RTstdDevPos, RTstdDevDepth, reader.stdDevPos, reader.stdDevDep, thu, tvu, thuaccepted, tvuaccepted))
# 			lastTimeStamp = reader.timestamp

# 	reportptr.close()

# ###############################################################################
# def computepetrobrastvu(depth=0):
# 	'''compute the TVU and THU permissible error specification based on AUV depth and client specific TVU formula'''

# 	# compute the Total Horizontal Uncertainty, which is 0.5% waterdepth + 1.0m (for free) to a 95% confidence level
# 	thu = 1 + (depth * 0.005)
# 	# compute the Total Vertical Uncertainty, which is 0.1% waterdepth + 0.5m (for free) to a 95% confidence level
# 	tvu = 0.5 + (depth * 0.001)

# 	return thu, tvu

###############################################################################
def setssdmarchivefields():
	fields = []
	fields.append(datetime.now().date())
	fields.append(os.getenv('username'))
	return fields

###############################################################################
def setssdmobjectfields():
	# featureid 		= 0

	# featureid 		= uuid.UUID()
	objectid 		= None
	featureid 		= str(uuid.uuid4())
	surveyid 		= ssdmfieldvalue.readvalue('survey_id')
	surveyidref 	= ssdmfieldvalue.readvalue('survey_id_ref')
	remarks 		= ssdmfieldvalue.readvalue('remarks')
	
	fields = []
	fields.append(objectid)
	fields.append(featureid)
	fields.append(surveyid)
	fields.append(surveyidref)
	fields.append(remarks)
	return fields
	
# ###############################################################################
# def createsurveyctd(reader, table, geo, surveyname):
# 	'''read a CTD profile and create a SSDM TSDip_Sample_Pnt into a geopackage'''

# 	archivefields = setssdmarchivefields()
# 	objectfields = setssdmobjectfields()

# 	reader.rewind() #rewind to the start of the file
# 	while reader.moreData() > 0:
# 		reader.readDatagram()

# 		x,y = geo.convertToGrid(float(reader.longitude),float(reader.latitude))
# 		# remarks 		= surveyname
# 		samplename 		= reader.fileName
# 		sampledesc		= surveyname
# 		samplemethod	= "AUV Survey"
# 		samplingdate 	= from_timestamp(reader.ts).date()
# 		dataurl 		= ssdmfieldvalue.readvalue("DATA_URL")
# 		reporturl 		= ssdmfieldvalue.readvalue("REPORT_URL")
# 		surveydate 		= from_timestamp(reader.ts).date()
# 		projectname		= surveyname
# 		fromtime		= from_timestamp(reader.ts).strftime("%H:%M:%S")
# 		totime			= from_timestamp(reader.ts).strftime("%H:%M:%S")
# 		instrumentused	= ssdmfieldvalue.readvalue("INSTRUMENT_USED")
# 		locality 		= "locality"
# 		symbologycode 	= ""

# 		# write out the FIELDS data
# 		fielddata = []
# 		fielddata += archivefields
# 		fielddata += objectfields

# 		fielddata.append(samplename)
# 		fielddata.append(sampledesc)
# 		fielddata.append(samplemethod)
# 		fielddata.append(samplingdate)

# 		fielddata.append(dataurl)
# 		fielddata.append(reporturl)
# 		fielddata.append(surveydate)
# 		fielddata.append(projectname)
# 		fielddata.append(fromtime)

# 		fielddata.append(totime)
# 		fielddata.append(instrumentused)
# 		# fielddata.append(os.getenv('username'))
# 		# fielddata.append(preparedDate)
# 		fielddata.append(reader.temperature)
# 		fielddata.append(reader.salinity)	
# 		fielddata.append(reader.pressure)

# 		fielddata.append(reader.velocity)
# 		fielddata.append(reader.conductivity)
# 		fielddata.append(reader.density)
# 		fielddata.append(reader.depth)
# 		fielddata.append(locality)

# 		fielddata.append(symbologycode)

# 		# now write the point to the table.
# 		table.addpointrecord(x, y, fielddata)		
	
# 	table.close()
# ###############################################################################
# def createsurveytrack(filename, navigation, table, geo):
# 	'''read a survey.mp file and create a SSDM geopackage'''
# 	totalDistanceRun = 0

# 	for position in navigation:
# 		line = []
# 		distance = 0
# 		linename = filename[:254]
# 		# x,y = geo.convertToGrid(float(wpt.longitude),float(wpt.latitude))
# 		line.append(position[1]
# 		line.append(position[2])

# 		distance, alpha1Tp2, alpha21 = geodetic.calculateRangeBearingFromGeographicals(surveyLine.x1, surveyLine.y1,  surveyLine.x2,  surveyLine.y2 )
# 		heading = alpha1Tp2
# 		# distance += geodetic.est_dist(wpt.latitude, wpt.longitude, prevY, prevX)
# 		# prevX = wpt.longitude
# 		# prevY = wpt.latitude
			
# 		surveyname 		= ssdmfieldvalue.readvalue("SURVEY_NAME")
# 		lineprefix 		= linename
# 		# linename 		= surveyname[:20]
# 		# heading 		= 0

# 		userName = os.getenv('username')
# 		# filename = os.path.basename(reader.fileName)
# 		preparedDate = datetime.now()

# 		symbologycode 	= "TBA"
# 		projectname		= surveyname
# 		surveyblockname	= surveyname

# 		# write out the FIELDS data
# 		fielddata = []
# 		fielddata += setssdmarchivefields()
# 		fielddata += setssdmobjectfields()

# 		fielddata.append(surveyname)
# 		fielddata.append(lineprefix)
# 		fielddata.append(linename)		
# 		fielddata.append(heading)
# 		fielddata.append(symbologycode)

# 		fielddata.append(projectname)
# 		fielddata.append(surveyblockname)
# 		fielddata.append(userName)
# 		fielddata.append(preparedDate)
# 		fielddata.append(userName)

# 		fielddata.append(preparedDate)
# 		fielddata.append("")
# 		fielddata.append(distance)

# 		# now write the point to the table.
# 		table.addlinestringrecord(line, fielddata)		
	
# 	table.close()


###############################################################################
def createsurveyplan(reader, table, geo):
	'''read a survey.mp file and create a SSDM geopackage'''
	totalDistanceRun = 0

	for surveyLine in reader.surveylines:
		line = []
		distance = 0
		linename = surveyLine.name[:254]
		# x,y = geo.convertToGrid(float(wpt.longitude),float(wpt.latitude))
		line.append(surveyLine.x1)
		line.append(surveyLine.y1)
		line.append(surveyLine.x2)
		line.append(surveyLine.y2)

		distance, alpha1Tp2, alpha21 = geodetic.calculateRangeBearingFromGeographicals(surveyLine.x1, surveyLine.y1,  surveyLine.x2,  surveyLine.y2 )
		heading = alpha1Tp2
		# distance += geodetic.est_dist(wpt.latitude, wpt.longitude, prevY, prevX)
		# prevX = wpt.longitude
		# prevY = wpt.latitude
			
		surveyname 		= ssdmfieldvalue.readvalue("SURVEY_NAME")
		lineprefix 		= linename
		# linename 		= surveyname[:20]
		# heading 		= 0

		userName = os.getenv('username')
		# filename = os.path.basename(reader.fileName)
		preparedDate = datetime.now()

		symbologycode 	= "TBA"
		projectname		= surveyname
		surveyblockname	= surveyname

		# write out the FIELDS data
		fielddata = []
		fielddata += setssdmarchivefields()
		fielddata += setssdmobjectfields()

		fielddata.append(surveyname)
		fielddata.append(lineprefix)
		fielddata.append(linename)		
		fielddata.append(heading)
		fielddata.append(symbologycode)

		fielddata.append(projectname)
		fielddata.append(surveyblockname)
		fielddata.append(userName)
		fielddata.append(preparedDate)
		fielddata.append(userName)

		fielddata.append(preparedDate)
		fielddata.append("")
		fielddata.append(distance)

		# now write the point to the table.
		table.addlinestringrecord(line, fielddata)		
	
	table.close()

# ###############################################################################
# def createTrackPoint(reader, navigation, pointtable, step, geo, surveyname="", usblobservations=None):
# 	''' writes in format compliant with SSDM.createPointShapeFile2'''
# 	lastTimeStamp 		= 0
# 	recTime 			= 0
# 	recTimeString 		= ""
# 	longitude 			= 0
# 	latitude 			= 0
# 	depth 				= 0
# 	roll 				= 0
# 	pitch 				= 0
# 	heading 			= 0
# 	# timeIDX				= 0
# 	# latitudeIDX			= 0
# 	# longitudeIDX		= 0
# 	# standardDeviation	= 0
# 	thu					= 0
# 	tvu					= 0
# 	usblage 			= 0
# 	utpage				= 0
# 	thuaccepted			= 0
# 	tvuaccepted			= 0
	
# 	timeIDX				= 0
# 	longitudeIDX		= 1
# 	latitudeIDX			= 2
# 	depthIDX 			= 3
# 	headingIDX 			= 4
# 	rollIDX 			= 5
# 	pitchIDX 			= 6

# 	contractorname = ssdmfieldvalue.readvalue("CONTRACTOR_NAME")

# 	for update in navigation:
# 		recTime 	= update[timeIDX] #unixtime
# 		longitude 	= update[longitudeIDX]
# 		latitude 	= update[latitudeIDX]
# 		depth 		= update[depthIDX]
# 		heading 	= update[headingIDX]
# 		pitch 		= update[pitchIDX]
# 		roll 		= update[rollIDX]
# 		# optimise...
# 		if recTime - lastTimeStamp < step:
# 			continue

# 		# if USBL is provided, extract the nearest record...
# 		if usblobservations is None:
# 			usblage = 0
# 		else:
# 			usbltime, SD = usblobservations.getNearestAt(recTime)
# 			usblage = recTime - usbltime

# 		if latitude == 0 or longitude == 0:
# 			continue
# 		lastTimeStamp = recTime
# 		x,y = geo.convertToGrid(longitude, latitude)
# 		# recDate = from_timestamp(recTime).strftime("%Y%m%d")
# 		recTimeString = from_timestamp(recTime).strftime("%H:%M:%S")
# 		# write out the shape file FIELDS data
# 		# userName = os.getenv('username')
# 		filename 			= os.path.basename(reader.fileName)
# 		lineid 				= 0
# 		linename 			= filename[:40]
# 		lastseisptid 		= 0
# 		symbologycode 		= "symbologycode"
# 		datasource 			= filename
# 		linelength 			= 0
# 		firstseisptid 		= 0
# 		hiresseismiceqlurl 	= ""
# 		otherdataurl 		= ""
# 		layer 				= "TBA"
# 		shapelength 		= 0
# 		stdDevPos 			= 0.0
# 		stdDevDep 			= 0.0
		
# 		fielddata = []
# 		fielddata += setssdmarchivefields()
# 		fielddata += setssdmobjectfields()

# 		fielddata.append(lineid)
# 		fielddata.append(linename)
# 		fielddata.append(lastseisptid)
# 		fielddata.append(symbologycode)
# 		fielddata.append(datasource)
		
# 		fielddata.append(contractorname)
# 		fielddata.append(linelength)
# 		fielddata.append(firstseisptid)
# 		fielddata.append(hiresseismiceqlurl)
# 		fielddata.append(otherdataurl)
		
# 		fielddata.append(layer)
# 		fielddata.append(shapelength)
# 		fielddata.append(recTimeString)
# 		fielddata.append(lastTimeStamp)
# 		fielddata.append(longitude)
		
# 		fielddata.append(latitude)
# 		fielddata.append(depth)
# 		fielddata.append(roll)
# 		fielddata.append(pitch)
# 		fielddata.append(heading)
		
# 		fielddata.append(stdDevPos)
# 		fielddata.append(stdDevDep)
# 		fielddata.append(usblage)
# 		fielddata.append(utpage)
# 		fielddata.append(thu)
		
# 		fielddata.append(tvu)
# 		fielddata.append(thuaccepted)
# 		fielddata.append(tvuaccepted)

# 		# now write the point to the table.
# 		pointtable.addpointrecord(x, y, fielddata)		
	
# 	pointtable.close()

# ###############################################################################
# def createTrackPointfromUTP(reader, pointtable, step, geo, tslongitude, tslatitude, tsstandardeviation, UTPQCFileName, surveyname=""):
# 	recTime 			= 0
# 	recTimeString 		= ""
# 	longitude 			= 0
# 	latitude 			= 0
# 	cminuso				= 0 #the difference between the UTP observed range than the AUV position to the UTP beacon.
# 	acceptancethreshold = 0

# 	# create the CSV QC file...
# 	if os.path.isfile(UTPQCFileName):
# 		outfileptr = open(UTPQCFileName, 'a')
# 	else:
# 		outfileptr = open(UTPQCFileName, 'w')
# 		outfileptr.write("Time, TPID, AUVLongitude, AUVLatitude, AUVPositionStandardDeviation, TPLongitude, TPLatitude, TPDepth, CalculatedRange, ObservedRange\n")

# 	reader.rewind() #rewind to the start of the file
# 	while reader.moreData() > 0:
# 		reader.readDatagram()
# 		UTPrange 	= reader.record[7]
# 		if UTPrange == 0:
# 			continue #dont bother plotting zero range.
# 		# now find the AUV position when the UTP observation was made...
# 		auvlongitude = tslongitude.getValueAt(reader.record[reader.timeIDX])
# 		auvlatitude = tslatitude.getValueAt(reader.record[reader.timeIDX])
# 		standarddeviation = tsstandardeviation.getValueAt(reader.record[reader.timeIDX])
# 		#x,y = geo.convertToGrid(longitude, latitude)
# 		recDate = from_timestamp(reader.record[reader.timeIDX]).strftime("%Y%m%d")
# 		recTimeString = from_timestamp(reader.record[reader.timeIDX]).strftime("%H:%M:%S")

# 		tpID 			= reader.record[0]
# 		tpLongitude 	= reader.record[2]
# 		tpLatitude 		= reader.record[1]
# 		tpDepth 		= reader.record[3]
# 		observedrange 	= reader.record[7]
# 		soundspeed 		= reader.record[11]
		
# 		#compute the calculated range between utp transponder and navlab position so we can compute a bearing
# 		calculatedrange, brg1, brg2 = geodetic.calculateRangeBearingFromGeographicals(auvlongitude, auvlatitude, tpLongitude, tpLatitude)

# 		# we should compute the end of the utp range rather than plot the auv coordinate
# 		latitude, longitude, brg = geodetic.calculateGeographicalPositionFromRangeBearing(tpLatitude, tpLongitude, brg2, observedrange)
# 		x,y = geo.convertToGrid(longitude, latitude)
		
# 		cminuso = calculatedrange - observedrange #calculated - observed range
# 		# now compute the threshold for acceptance based on water depth.
# 		# use formula 0.5% waterdepth + 1m as the threshold for accept / reject
# 		threshold = (tpDepth * 0.005) + 1.0
# 		if standarddeviation > threshold:
# 			acceptancethreshold = 0 #nav is rejected
# 		else:
# 			acceptancethreshold = 1 #nav is accepted.

# 		fielddata = []
# 		fielddata.append(tpID)
# 		fielddata.append(recDate)
# 		fielddata.append(recTimeString)
# 		fielddata.append(int(reader.record[reader.timeIDX]))
# 		fielddata.append(longitude)
# 		fielddata.append(latitude)
# 		fielddata.append(tpLongitude)
# 		fielddata.append(tpLatitude)
# 		fielddata.append(tpDepth)
# 		fielddata.append(observedrange)
# 		fielddata.append(standarddeviation)
# 		fielddata.append(soundspeed)
# 		fielddata.append(cminuso)
# 		fielddata.append(acceptancethreshold)

# 		# now write the point to the table.
# 		pointtable.addpointrecord(x, y, fielddata)		
		
# 		# lets write a csv so we can drop all this into excel for further analysis.
# 		outfileptr.write("%s,%s,%f,%f,%f,%f,%f,%f,%f,%f\n" % (from_timestamp(reader.record[reader.timeIDX]), tpID, longitude, latitude, standarddeviation, tpLongitude, tpLatitude, tpDepth, calculatedrange, observedrange))
	
# 	# pointtable.close()
# 	outfileptr.close()

# # ###############################################################################
# def createRangeLinesFromUSBL(reader, linetable, step, geo, tslongitude, tslatitude, tsstandardeviation, surveyname=""):
# 	recTime 			= 0
# 	recTimeString 		= ""
# 	longitude 			= 0
# 	latitude 			= 0

# 	reader.rewind() #rewind to the start of the file
# 	while reader.moreData() > 0:
# 		reader.readDatagram()
# 		UTPrange 	= reader.record[7]
# 		if UTPrange == 0:
# 			continue #dont bother plotting zero range.

# 		line = []

# 		# now find the AUV position when the UTP observation was made...
# 		auvlongitude 		= tslongitude.getValueAt(reader.record[reader.timeIDX])
# 		auvlatitude 		= tslatitude.getValueAt(reader.record[reader.timeIDX])
# 		standarddeviation 	= tsstandardeviation.getValueAt(reader.record[reader.timeIDX])
		
# 		# now add the seabed transponder position at UTP observation time...
# 		x,y = geo.convertToGrid(reader.record[2],reader.record[1])
# 		line.append(x)
# 		line.append(y)

# 		# now make the field attributes...
# 		recDate 		= from_timestamp(reader.record[reader.timeIDX]).strftime("%Y%m%d")
# 		recTimeString 	= from_timestamp(reader.record[reader.timeIDX]).strftime("%H:%M:%S")
# 		tpID 			= reader.record[0]
# 		tpLongitude 	= reader.record[2]
# 		tpLatitude 		= reader.record[1]
# 		tpDepth 		= reader.record[3]
# 		observedrange 	= reader.record[7]
# 		soundspeed 		= reader.record[11]

# 		#compute the calculated range between utp transponder and navlab position so we can compute a bearing
# 		calculatedrange, brg1, brg2 = geodetic.calculateRangeBearingFromGeographicals(auvlongitude, auvlatitude, tpLongitude, tpLatitude)

# 		# we should compute the end of the utp range rather than plot the auv coordinate
# 		latitude, longitude, brg = geodetic.calculateGeographicalPositionFromRangeBearing(tpLatitude, tpLongitude, brg2, observedrange)
# 		x,y = geo.convertToGrid(longitude, latitude)
# 		line.append(x)
# 		line.append(y)

# 		cminuso = calculatedrange - observedrange #calculated - observed range
# 		# now compute the threshold for acceptance based on water depth.
# 		# use formula 0.5% waterdepth + 1m as the threshold for accept / reject
# 		threshold = (tpDepth * 0.005) + 1.0
# 		if standarddeviation > threshold:
# 			acceptancethreshold = 0 #nav is rejected
# 		else:
# 			acceptancethreshold = 1 #nav is accepted.

# 		fielddata = []
# 		fielddata.append(tpID)
# 		fielddata.append(recDate)
# 		fielddata.append(recTimeString)
# 		fielddata.append(int(reader.record[reader.timeIDX]))
# 		fielddata.append(longitude)
# 		fielddata.append(latitude)
# 		fielddata.append(tpLongitude)
# 		fielddata.append(tpLatitude)
# 		fielddata.append(tpDepth)
# 		fielddata.append(observedrange)
# 		fielddata.append(standarddeviation)
# 		fielddata.append(soundspeed)
# 		fielddata.append(cminuso)
# 		fielddata.append(acceptancethreshold)

# 		# now write the point to the table.
# 		linetable.addlinestringrecord(line, fielddata)		
# 	# linetable.close()
# # ###############################################################################
# def createRangeLinesFromUTP(reader, linetable, step, geo, tslongitude, tslatitude, tsstandardeviation, surveyname=""):
# 	recTime 			= 0
# 	recTimeString 		= ""
# 	longitude 			= 0
# 	latitude 			= 0

# 	reader.rewind() #rewind to the start of the file
# 	while reader.moreData() > 0:
# 		reader.readDatagram()
# 		UTPrange 	= reader.record[7]
# 		if UTPrange == 0:
# 			continue #dont bother plotting zero range.

# 		line = []

# 		# now find the AUV position when the UTP observation was made...
# 		auvlongitude 		= tslongitude.getValueAt(reader.record[reader.timeIDX])
# 		auvlatitude 		= tslatitude.getValueAt(reader.record[reader.timeIDX])
# 		standarddeviation 	= tsstandardeviation.getValueAt(reader.record[reader.timeIDX])
		
# 		# now add the seabed transponder position at UTP observation time...
# 		x,y = geo.convertToGrid(reader.record[2],reader.record[1])
# 		line.append(x)
# 		line.append(y)

# 		# now make the field attributes...
# 		recDate 		= from_timestamp(reader.record[reader.timeIDX]).strftime("%Y%m%d")
# 		recTimeString 	= from_timestamp(reader.record[reader.timeIDX]).strftime("%H:%M:%S")
# 		tpID 			= reader.record[0]
# 		tpLongitude 	= reader.record[2]
# 		tpLatitude 		= reader.record[1]
# 		tpDepth 		= reader.record[3]
# 		observedrange 	= reader.record[7]
# 		soundspeed 		= reader.record[11]

# 		#compute the calculated range between utp transponder and navlab position so we can compute a bearing
# 		calculatedrange, brg1, brg2 = geodetic.calculateRangeBearingFromGeographicals(auvlongitude, auvlatitude, tpLongitude, tpLatitude)

# 		# we should compute the end of the utp range rather than plot the auv coordinate
# 		latitude, longitude, brg = geodetic.calculateGeographicalPositionFromRangeBearing(tpLatitude, tpLongitude, brg2, observedrange)
# 		x,y = geo.convertToGrid(longitude, latitude)
# 		line.append(x)
# 		line.append(y)

# 		cminuso = calculatedrange - observedrange #calculated - observed range
# 		# now compute the threshold for acceptance based on water depth.
# 		# use formula 0.5% waterdepth + 1m as the threshold for accept / reject
# 		threshold = (tpDepth * 0.005) + 1.0
# 		if standarddeviation > threshold:
# 			acceptancethreshold = 0 #nav is rejected
# 		else:
# 			acceptancethreshold = 1 #nav is accepted.

# 		fielddata = []
# 		fielddata.append(tpID)
# 		fielddata.append(recDate)
# 		fielddata.append(recTimeString)
# 		fielddata.append(int(reader.record[reader.timeIDX]))
# 		fielddata.append(longitude)
# 		fielddata.append(latitude)
# 		fielddata.append(tpLongitude)
# 		fielddata.append(tpLatitude)
# 		fielddata.append(tpDepth)
# 		fielddata.append(observedrange)
# 		fielddata.append(standarddeviation)
# 		fielddata.append(soundspeed)
# 		fielddata.append(cminuso)
# 		fielddata.append(acceptancethreshold)

# 		# now write the point to the table.
# 		linetable.addlinestringrecord(line, fielddata)		
# 	# linetable.close()


# ###############################################################################
# def creatembescoverage(reader, table, step, geo, surveyname=""):
# 	'''write out each polygon for this MBES file (there can be several) '''
# 	polygons = all2coverage.extractMBESCoverage(reader, step, geo)
# 	for p in polygons:

# 		# write out the FIELDS data
# 		userName = os.getenv('username')
# 		fielddata = []
# 		fielddata += setssdmarchivefields()
# 		fielddata += setssdmobjectfields()


# 		# fielddata.append(datetime.now().date())
# 		# fielddata.append(os.getenv('username'))
# 		# fielddata.append(0)
# 		# fielddata.append(0)
# 		# fielddata.append(reader.fileName)
# 		# fielddata.append(reader.fileName)
# 		fielddata.append(0)
# 		fielddata.append(reader.fileName[:40])
# 		fielddata.append(0)
# 		fielddata.append(reader.fileName)
# 		fielddata.append(userName)
# 		fielddata.append(0)
# 		fielddata.append(0)
# 		fielddata.append("")
# 		fielddata.append("")
# 		fielddata.append(surveyname)
# 		fielddata.append(0)
			
# 		# now write the point to the table.
# 		table.addpolygonrecord(p, fielddata)		
# 		table.close()



###############################################################################
def from_timestamp(unixtime):
	return datetime(1970, 1 ,1) + timedelta(seconds=unixtime)

###############################################################################
def to_timestamp(recordDate):
	return (recordDate - datetime(1970, 1, 1)).total_seconds()

###############################################################################
def	makedirs(odir):
	if not os.path.isdir(odir):
		os.makedirs(odir, exist_ok=True)
	odirlog = os.path.join(odir, "log").replace('\\','/')
	if not os.path.isdir(odirlog):
		os.makedirs(odirlog)
	return odirlog

###############################################################################
if __name__ == "__main__":
	main()
