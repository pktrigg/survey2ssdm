#name:		  	kmall
#created:		November 2018
#by:			paul.kennedy@guardiangeomatics.com
#description:   python module to read a Kongsberg KMALL and KMWCD sonar file
#notes:		 	See main at end of script for example how to use this
#based on 20170301_kmall datagram format.pdf

# See readme.md for more details
# Data Type Conversions from KMALL to Python::     
# https://docs.python.org/3/library/struct.html
# uint32 	= 4 bytes 		= L
# uint8		= 1 byte 		= B
# unit16	= 2 bytes 		= H

# import ctypes
# import math
import os.path
import pprint
# import re
import struct
import sys
import time
import numpy as np
from argparse import ArgumentParser
from datetime import datetime, timedelta
import glob

# from sqlalchemy import false
import timeseries

###########################################################################
def main():
	parser = ArgumentParser(description='Read a KMALL file.')
	parser.add_argument('-i', dest='inputFile', action='store', default="", help='Input filename.pos to process.')
	
	files = []
	try:
		args = parser.parse_args()
		if len (args.inputFile) == 0:
			# no file is specified, so look for a .pos file in terh current folder.
			inputfolder = os.getcwd()
			files = findFiles2(False, inputfolder, "*.kmall")
		else:
			files.append(args.inputFile)

		for file in files:
			print ("processing file: %s" % (file))
			process(file)
	except:
		#open the ALL file for reading by creating a new kmallreader class and passin in the filename to open.
		filename =   "C:/sampledata/kmall/B_S2980_3005_20220220_084910.kmall"
		extract2timeseries(filename)
		# process(filename)

###############################################################################
###############################################################################
def findFiles2(recursive, filespec, filter):
	'''tool to find files based on user request.  This can be a single file, a folder start point for recursive search or a wild card'''
	matches = []
	if recursive:
		matches = glob(os.path.join(filespec, "**", filter), recursive = True)
	else:
		matches = glob(os.path.join(filespec, filter))
	
	mclean = []
	for m in matches:
		mclean.append(m.replace('\\','/'))
		
	# if len(mclean) == 0:
	# 	print ("Nothing found to convert, quitting")
		# exit()
	return mclean

###############################################################################
def extract2timeseries(filename):
	'''something like this will create a list of x,y,z,r,p,h for each ping time...'''

	import timeseries as ts

	r = kmallreader(filename)

	print("load the attitude to lists...")
	attitude = r.loadattitude()
	print("load the ping header data to lists...")
	pings = r.loadpingnavigation()

	# convert the attitudes into time series so we can interpolate
	timestamps = [i[0] for i in attitude]
	list_x = [i[1] for i in attitude]
	list_y = [i[2] for i in attitude]
	list_z = [i[3] for i in attitude]
	list_roll = [i[4] for i in attitude]
	list_pitch = [i[5] for i in attitude]
	list_heading = [i[6] for i in attitude]
	
	csx = ts.cTimeSeries(timestamps, list_x)
	csy = ts.cTimeSeries(timestamps, list_y)
	csz = ts.cTimeSeries(timestamps, list_z)
	csroll = ts.cTimeSeries(timestamps, list_roll)
	cspitch = ts.cTimeSeries(timestamps, list_pitch)
	csheading = ts.cTimeSeries(timestamps, list_heading)

	# now interpolate
	for p in pings:
		x = csx.getValueAt(p[0])
		y = csy.getValueAt(p[0])
		z = csz.getValueAt(p[0])
		roll = csroll.getValueAt(p[0])
		pitch = cspitch.getValueAt(p[0])
		heading = csheading.getValueAt(p[0])
		
		print(p[0],x,y,z,roll,pitch,heading)

############################################################
def process(filename):

	r = kmallreader(filename)

	# demonstrate how to load the navigation records into a list.  this is really handy if we want to make a trackplot for coverage
	start_time = time.time() # time the process
	print("Loading Navigation...")
	navigation = r.loadNavigation(step=1)
	# print(navigation)
	print("Read Duration: %.3f seconds, navcount %d" % (time.time() - start_time, len(navigation))) # print the processing time. It is handy to keep an eye on processing performance.

	print("Loading Point Cloud...")
	pointcloud = Cpointcloud()
	pingCount = 0
	start_time = time.time() # time the process
	while r.moreData():
		# read a datagram.  If we support it, return the datagram type and aclass for that datagram
		# The user then needs to call the read() method for the class to undertake a fileread and binary decode.  This keeps the read super quick.
		typeofdatagram, datagram = r.readDatagram()
		# print("%s,%d" % (typeofdatagram, r.fileptr.tell()), end='')

		# if typeofdatagram == '#IIP':
		# 	datagram.read()
		# 	print (datagram.installationparameters)
		# if typeofdatagram == '#IOP':
		# 	datagram.read()
		# 	print (datagram.runtimeparameters)
		# if typeofdatagram == '#SVP':
		# 	datagram.read()
		# 	print (datagram.data)
		# if typeofdatagram == '#SCL':
		# 	datagram.read()
		# 	print (datagram.data)
		# if typeofdatagram == '#SKM':
		# 	datagram.read()
		# if typeofdatagram == '#SPO':
		# 	datagram.read()
		if typeofdatagram == '#MRZ':
			datagram.read()
			x, y, z = computebathypointcloud(datagram)
			pointcloud.add(x, y, z)
			#now georeference by computing the actual position on the seafloor
			# for a in datagram.Attitude:
			#	 print ("%.5f, %.3f, %.3f, %.3f, %.3f" % (r.to_timestamp(r.to_DateTime(a[0], a[1])), a[3], a[4], a[5], a[6]))
			
		continue

	outfile = os.path.join(os.path.dirname(filename), os.path.basename(filename) + ".txt")
	xyz = np.column_stack([pointcloud.xarr,pointcloud.yarr, pointcloud.zarr])
	print("Saving point cloud to %s" % (outfile)) 
	np.savetxt(outfile, (xyz), fmt='%.10f', delimiter=',')
	r.rewind()
	print("Complete reading ALL file :-)")
	r.close()


###############################################################################
def computebathypointcloud(datagram):
	'''using the MRZ datagram, efficiently compute a numpy array of the point clouds  '''
	npdeltaLatitude_deg = np.fromiter((beam.deltaLatitude_deg for beam in datagram.beams), float, count=len(datagram.beams)) #. Also, adding count=len(stars)
	npdeltaLongitude_deg = np.fromiter((beam.deltaLongitude_deg for beam in datagram.beams), float, count=len(datagram.beams)) #. Also, adding count=len(stars)
	npz_reRefPoint_m = np.fromiter((beam.z_reRefPoint_m for beam in datagram.beams), float, count=len(datagram.beams)) #. Also, adding count=len(stars)

	# we can now comput absolute positions from the relative positions
	npLatitude_deg = npdeltaLatitude_deg + datagram.latitude_deg
	npLongitude_deg = npdeltaLongitude_deg + datagram.longitude_deg
	return (npLongitude_deg, npLatitude_deg, npz_reRefPoint_m)

###############################################################################
def decodeheader(s, obj):
	obj.numberofbytes		= s[0]
	obj.typeofdatagram		= s[1].decode('utf-8').rstrip('\x00')
	obj.version				= s[2]
	obj.systemid			= s[3]
	obj.echosounderid		= s[4]
	obj.time_sec			= s[5]
	obj.time_nanosec		= s[6]
	obj.date 				= from_timestamp(obj.time_sec + obj.time_nanosec/1000000000)
	return obj

###############################################################################
class Cpointcloud:
	'''class to hold a point cloud'''
	xarr = np.empty([0], dtype=float)
	yarr = np.empty([0], dtype=float)
	zarr = np.empty([0], dtype=float)

	###############################################################################
	def __init__(self, npx=None, npy=None, npz=None):
		'''add the new ping of data to the existing array '''
		np.append(self.xarr, np.array(npx))
		np.append(self.yarr, np.array(npy))
		np.append(self.zarr, np.array(npz))

	###############################################################################
	def add(self, npx, npy, npz):
		'''add the new ping of data to the existing array '''
		self.xarr = np.append(self.xarr, np.array(npx))
		self.yarr = np.append(self.yarr, np.array(npy))
		self.zarr = np.append(self.zarr, np.array(npz))

###############################################################################
class kmallreader:
	'''class to read a Kongsberg EM multibeam .all file'''
	EMdgmHeader_def = '=L4sBBHLL' 
	KMALLPacketHeader_len = struct.calcsize(EMdgmHeader_def)
	KMALLPacketHeader_unpack = struct.Struct(EMdgmHeader_def).unpack_from

	MAX_SPO_DATALENGTH = 250
	MAX_ATT_DATALENGTH = 250
	MAX_SVT_DATALENGTH = 64
	MAX_SCL_DATALENGTH = 64
	MAX_SDE_DATALENGTH = 32
	MAX_SHI_DATALENGTH = 32
	MAX_CPO_DATALENGTH = 250
	MAX_CHE_DATALENGTH = 64
	UNAVAILABLE_POSFIX = 0xffff
	MAX_SIDESCAN_SAMP= 60000
	MAX_SIDESCAN_EXTRA_SAMP= 15000

	EMdgmScommon_def 			= '4H' 
	EMdgmSCLdataFromSensor_def 	= "fL%ss" % (MAX_SCL_DATALENGTH)

	EMdgmSKMinfo_def 			= "H2B4H"

	KMbinary_def				= "4sHHLLL ddf 4f 3f 3f 7f 3f"
	KMdelayedHeave_def			= "LLf"

	EMdgmSKMsample_def 			= "=" + KMbinary_def + KMdelayedHeave_def

	EMdgmScommon_def			= "4H"

	EMdgmSPOdataBlock_def		= "=2Lf2d3f%ss" % (MAX_SPO_DATALENGTH)
	EMdgmSPOdataBlock_def		= "=2Lf2d3f" 

	EMdgmMpartition_def			= "=2H"

	###############################################################################
	def __init__(self, filename):
		if not os.path.isfile(filename):
			print ("file not found:", filename)
		self.fileName = filename
		self.fileptr = open(filename, 'rb')
		self.fileSize = os.path.getsize(filename)
		# self.recordDate = ""
		self.recordTime = ""
		self.recordCounter=0

	###############################################################################
	def __str__(self):
		return pprint.pformat(vars(self))

	###############################################################################
	def currentRecordDateTime(self):
		'''return a python date object from the current datagram objects raw date and time fields '''
		if self.recordDate == 0:
			return datetime.now()
		# if self.recordTime < 2:
		# 	print (self.recordDate, self.recordTime)
		try:
			date_object = datetime.strptime(str(self.recordDate), '%Y%m%d') + timedelta(0,self.recordTime)
		except:
			return datetime.now()

		return date_object

	###############################################################################
	def to_DateTime(self, recordDate, recordTime):
		'''return a python date object from a split date and time record'''
		date_object = datetime.strptime(str(recordDate), '%Y%m%d') + timedelta(0,recordTime)
		return date_object

	# def to_timestamp(self, dateObject):
	#	 '''return a unix timestamp from a python date object'''
	#	 return (dateObject - datetime(1970, 1, 1)).total_seconds()

	###############################################################################
	def close(self):
		'''close the current file'''
		self.fileptr.close()

	###############################################################################
	def rewind(self):
		'''go back to start of file'''
		self.fileptr.seek(0, 0)

	###############################################################################
	def currentPtr(self):
		'''report where we are in the file reading process'''
		return self.fileptr.tell()

	###############################################################################
	def moreData(self):
		'''report how many more bytes there are to read from the file'''
		bytesremaining = self.fileSize - self.fileptr.tell()
		# trap out incorrectly closed files.  we have seenthis when sis crashes
		bytesremaining = max(bytesremaining,0)
		return bytesremaining

	###############################################################################
	def readDatagramHeader(self):
		'''read the common header for any datagram'''
		try:
			curr = self.fileptr.tell()
			data = self.fileptr.read(self.KMALLPacketHeader_len)
			s = self.KMALLPacketHeader_unpack(data)

			numberofbytes		= s[0]
			typeofdatagram		= s[1].decode('utf-8').rstrip('\x00')
			version				= s[2]
			systemid			= s[3]
			echosounderid		= s[4]
			time_sec			= s[5]
			time_nanosec		= s[6]
			self.date 			= from_timestamp(time_sec + time_nanosec/1000000000)
			# self.recordTime = RecordTime

			# now reset file pointer to the start of the datagram
			self.fileptr.seek(curr, 0)

			# we need to add 4 bytes as the message does not contain the 4 bytes used to hold the size of the message
			# trap corrupt datagrams at the end of a file.  We see this in EM2040 systems.
			# if (curr + numberofbytes + 4 ) > self.fileSize:
			# 	numberofbytes = self.fileSize - curr - 4
			# 	typeofdatagram = 'XXX'
			# 	return numberofbytes + 4, STX, typeofdatagram, EMModel, RecordDate, RecordTime

			return numberofbytes, typeofdatagram, version, systemid, echosounderid, time_sec, time_nanosec, self.date
		except struct.error:
			return 0,0,0,0,0,0,0,0

	###############################################################################
	def readDatagramBytes(self, offset, byteCount):
		'''read the entire raw bytes for the datagram without changing the file pointer.  this is used for file conditioning'''
		curr = self.fileptr.tell()
		self.fileptr.seek(offset, 0)# move the file pointer to the start of the record so we can read from disc
		data = self.fileptr.read(byteCount)
		self.fileptr.seek(curr, 0)
		return data

	###############################################################################
	def getRecordCount(self):
		'''read through the entire file as fast as possible to get a count of all records.  useful for progress bars so user can see what is happening'''
		count = 0
		start = 0
		end = 0
		self.rewind()
		numberofbytes, STX, typeofdatagram, EMModel, RecordDate, RecordTime = self.readDatagramHeader()
		start = to_timestamp(to_DateTime(RecordDate, RecordTime))
		self.rewind()
		while self.moreData():
			numberofbytes, STX, typeofdatagram, EMModel, RecordDate, RecordTime = self.readDatagramHeader()
			self.fileptr.seek(numberofbytes, 1)
			count += 1
		self.rewind()
		end = to_timestamp(to_DateTime(RecordDate, RecordTime))
		return count, start, end

	###############################################################################
	def readDatagram(self):
		'''read the datagram header.  This permits us to skip datagrams we do not support'''
		numberofbytes, typeofdatagram, version, systemid, echosounderid, time_sec, time_nanosec, date = self.readDatagramHeader()
		self.recordCounter += 1
		self.recordTime = time_sec + time_nanosec/1000000000
		if numberofbytes == 0:
			return "CORRUPT", None
	
		if typeofdatagram == '#IIP': # Installation (Start)
			dg = IIP_INSTALLATION(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		if typeofdatagram == '#IOP': # RUNTIME
			dg = IOP_RUNTIME(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		if typeofdatagram == '#SVP': # Sound Velocity
			dg = SVP(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		if typeofdatagram == '#SCL': # Clock
			dg = CLOCK(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		if typeofdatagram == '#SKM': # ATTITUDE
			dg = ATTITUDE(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		if typeofdatagram == '#SPO': # Position
			dg = POSITION(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		if typeofdatagram == '#MRZ': # Position
			dg = RANGEDEPTH(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		else:
			dg = UNKNOWN_RECORD(self.fileptr, numberofbytes, typeofdatagram)
			return dg.typeofdatagram, dg
			# self.fileptr.seek(numberofbytes, 1)

###############################################################################
	def loadNavigation(self, firstRecordOnly=False, step=0):
		'''loads all the navigation into lists'''
		navigation 					= []
		lastimestamp = 0
		self.rewind()
		while self.moreData():
			try:
				# print(self.fileptr.tell())
				typeofdatagram, datagram = self.readDatagram()
				if (typeofdatagram == 'CORRUPT'):
					#we have seen corrupt kmall files when sis crashes.
					self.rewind()
					return navigation

				if (typeofdatagram == '#SPO'):
					if (self.recordTime - lastimestamp) < step:
						# skip...  performance increase
						continue
					datagram.read()
					# trap bad values
					if datagram.latitude < -90:
						continue
					if datagram.latitude > 90:
						continue
					if datagram.longitude < -180:
						continue
					if datagram.longitude > 180:
						continue
					navigation.append([to_timestamp(datagram.date), datagram.longitude, datagram.latitude, 0.0, datagram.heading])
					lastimestamp = self.recordTime
					if firstRecordOnly: #we only want the first record, so reset the file pointer and quit
						self.rewind()
						return navigation
			except:
				e = sys.exc_info()[0]
				print("Error: %s.  Please check file.  it seems to be corrupt: %s" % (e, self.fileName))
		self.rewind()
		return navigation

###############################################################################
	def loadattitude(self):
		'''loads all the attitude into list'''
		attitude		= []
		lastimestamp 	= 0
		self.rewind()
		while self.moreData():
			try:
				# print(self.fileptr.tell())
				typeofdatagram, datagram = self.readDatagram()
				if (typeofdatagram == 'CORRUPT'):
					#we have seen corrupt kmall files when sis crashes.
					self.rewind()
					return attitude

				if (typeofdatagram == '#SKM'):
					datagram.read()
					for sample in datagram.data:
						timestamp = (sample[3] + sample[4]/1000000000)
						# print (from_timestamp(timestamp), sample[4]/1000000000)
						#time, x, y, z, roll, pitch, heading
						attitude.append([timestamp, sample[6], sample[7], sample[8], sample[9], sample[10], sample[11]])
			except:
				e = sys.exc_info()[0]
				print("Error: %s.  Please check file.  it seems to be corrupt: %s" % (e, self.fileName))
		self.rewind()
		return attitude

###############################################################################
	def loadpingnavigation(self):
		'''loads all the navigation from the PING into list so we can save as ASCII and inject into CARIS'''
		pingnavigation 					= []
		lastimestamp = 0
		self.rewind()
		
		while self.moreData():
			try:
				# print(self.fileptr.tell())
				typeofdatagram, datagram = self.readDatagram()
				if (typeofdatagram == 'CORRUPT'):
					#we have seen corrupt kmall files when sis crashes.
					self.rewind()
					return pingnavigation

				if (typeofdatagram == '#MRZ'):
					datagram.read(True)
					# trap bad values
					if datagram.latitude < -90:
						continue
					if datagram.latitude > 90:
						continue
					if datagram.longitude < -180:
						continue
					if datagram.longitude > 180:
						continue
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

					pingnavigation.append([to_timestamp(datagram.date), datagram.latitude, datagram.longitude, datagram.ellipsoidHeightReRefPoint_m, datagram.heading, 0.0, 0.0, 0.0])
					lastimestamp = self.recordTime
			except:
				e = sys.exc_info()[0]
				print("Error: %s.  Please check file.  it seems to be corrupt: %s" % (e, self.fileName))
		self.rewind()
		return pingnavigation

###############################################################################
	def getDatagramName(self, typeofdatagram):
		'''Convert the datagram type from the code to a user readable string.  Handy for displaying to the user'''
		#Multibeam Data
		# if (typeofdatagram == 'D'):
		# 	return "D_Depth"
		if (typeofdatagram == '#MRZ'):
			return "Depth"
		# if (typeofdatagram == 'K'):
		# 	return "K_CentralBeam"
		# if (typeofdatagram == 'F'):
		# 	return "F_RawRange"
		# if (typeofdatagram == 'f'):
		# 	return "f_RawRange"
		# if (typeofdatagram == 'N'):
		# 	return "N_RawRange"
		# if (typeofdatagram == 'S'):
		# 	return "S_SeabedImage"
		# if (typeofdatagram == 'Y'):
		# 	return "Y_SeabedImage"
		# if (typeofdatagram == 'k'):
		# 	return "k_WaterColumn"
		# if (typeofdatagram == 'O'):
		# 	return "O_QualityFactor"

		# ExternalSensors
		if (typeofdatagram == '#SKM'):
			return "Attitude"
		# if (typeofdatagram == 'n'):
		# 	return "network_Attitude"
		if (typeofdatagram == '#SCL'):
			return "Clock"
		if (typeofdatagram == '#SPO'):
			return "Position"
		# if (typeofdatagram == 'h'):
		# 	return "h_Height"
		# if (typeofdatagram == 'H'):
		# 	return "H_Heading"
		# if (typeofdatagram == 'E'):
		# 	return "E_SingleBeam"
		# if (typeofdatagram == 'T'):
		# 	return "T_Tide"

		# SoundSpeed
		# if (typeofdatagram == 'G'):
		# 	return "G_SpeedSoundAtHead"
		# if (typeofdatagram == 'U'):
		# 	return "U_SpeedSoundProfile"
		# if (typeofdatagram == 'W'):
		# 	return "W_SpeedSOundProfileUsed"

		# Multibeam parameters
		if (typeofdatagram == '#IIP'):
			return "Installation"
		if (typeofdatagram == '#IOP'):
			return "Runtime"
		# if (typeofdatagram == 'J'):
		# 	return "J_TransducerTilt"
		# if (typeofdatagram == '3'):
		# 	return "3_ExtraParameters"

		# # PU information and status
		# if (typeofdatagram == '0'):
		# 	return "0_PU_ID"
		# if (typeofdatagram == '1'):
		# 	return "1_PU_Status"
		# if (typeofdatagram == 'B'):
		# 	return "B_BIST_Result"


###############################################################################
class cBeam:
	def __init__(self, timestamp, decodestructure):
			# Data Fields
			self.timestamp 					= timestamp
			self.soundingIndex 				= decodestructure[0]
			self.txSectorNumb 				= decodestructure[1]
			# Detection info.
			self.detectionType 				= decodestructure[2]
			self.detectionMethod 			= decodestructure[3]
			self.rejectionInfo1 			= decodestructure[4]
			self.rejectionInfo2 			= decodestructure[5]
			self.postProcessingInfo 		= decodestructure[6]
			self.detectionClass 			= decodestructure[7]
			self.detectionConfidenceLevel 	= decodestructure[8]
			self.padding 					= decodestructure[9]
			self.rangeFactor 				= decodestructure[10]
			self.qualityFactor 				= decodestructure[11]
			self.detectionUncertaintyVer_m 	= decodestructure[12]
			self.detectionUncertaintyHor_m 	= decodestructure[13]
			self.detectionWindowLength_sec 	= decodestructure[14]
			self.echoLength_sec 			= decodestructure[15]
			# Water column paramters.
			self.WCBeamNumb 				= decodestructure[16]
			self.WCrange_samples 			= decodestructure[17]
			self.WCNomBeamAngleAcross_deg 	= decodestructure[18]
			# Reflectivity data (backscatter (BS) data).
			self.meanAbsCoeff_dBPerkm 		= decodestructure[19]
			self.reflectivity1_dB 			= decodestructure[20]
			self.reflectivity2_dB 			= decodestructure[21]
			self.receiverSensitivityApplied_dB 	= decodestructure[22]
			self.sourceLevelApplied_dB 			= decodestructure[23]
			self.BScalibration_dB 				= decodestructure[24]
			self.TVG_dB 						= decodestructure[25]
			# Range and angle data.
			self.beamAngleReRx_deg 				= decodestructure[26]
			self.beamAngleCorrection_deg 		= decodestructure[27]
			self.twoWayTravelTime_sec 			= decodestructure[28]
			self.twoWayTravelTimeCorrection_sec = decodestructure[29]
			# Georeferenced depth points.
			self.deltaLatitude_deg 				= decodestructure[30]
			self.deltaLongitude_deg 			= decodestructure[31]
			self.z_reRefPoint_m 				= decodestructure[32]
			self.y_reRefPoint_m 				= decodestructure[33]
			self.x_reRefPoint_m 				= decodestructure[34]
			self.beamIncAngleAdj_deg 			= decodestructure[35]
			self.realTimeCleanInfo 				= decodestructure[36]
			# Seabed image.
			self.SIstartRange_samples 			= decodestructure[37]
			self.SIcentreSample 				= decodestructure[38]
			self.SInumSamples 					= decodestructure[39]

###############################################################################
class ATTITUDE:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram 	= '#SKM'
		self.offset 			= fileptr.tell()
		self.numberofbytes 		= numberofbytes
		self.fileptr 			= fileptr
		self.data 				= []
		self.fileptr.seek(numberofbytes, 1)

	def read(self):
		self.fileptr.seek(self.offset, 0)
		rec_fmt = kmallreader.EMdgmHeader_def  + kmallreader.EMdgmSKMinfo_def
		rec_len 		= struct.calcsize(rec_fmt)
		rec_unpack 		= struct.Struct(rec_fmt).unpack_from
		s = rec_unpack(self.fileptr.read(rec_len))

		self.numberofbytes		= s[0]
		self.typeofdatagram		= s[1].decode('utf-8').rstrip('\x00')
		self.version			= s[2]
		self.systemid			= s[3]
		self.echosounderid		= s[4]
		self.time_sec			= s[5]
		self.time_nanosec		= s[6]
		self.date 				= from_timestamp(self.time_sec + self.time_nanosec/1000000000)

		self.numBytesInfoPart	= s[7]
		self.sensorSystem 		= s[8]
		self.sensorStatus 		= s[9]
		self.sensorInputFormat 		= s[10]
		self.numSamplesArray 		= s[11]
		self.numBytesPerSample 		= s[12]
		self.sensorDataContents		= s[13]

		# now read the attitude details... 
		rec_fmt = kmallreader.EMdgmSKMsample_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		# i = 0
		for i in range (self.numSamplesArray):
			data = self.fileptr.read(rec_len)
			s = rec_unpack(data)
			self.data.append(s)

		# # now read the attitude details... 
		# rec_fmt = kmallreader.EMdgmSKMsample_def
		# rec_len = struct.calcsize(rec_fmt)
		# rec_unpack = struct.Struct(rec_fmt).unpack
		# # i = 0
		# for i in range (self.numSamplesArray):
		# 	data = self.fileptr.read(rec_len)
		# 	s = rec_unpack(data)
		# 	self.data.append(s)


		# reset the file pointer to the end of teh packet.  for some reasdon we are 4 bytes out??? pkpk
		self.fileptr.seek(self.offset + self.numberofbytes, 0)

		# # self.numberofbytes= s[0]
		# self.STX			 	= s[1]
		# self.typeofdatagram  	= chr(s[2])
		# self.EMModel		 	= s[3]
		# self.RecordDate	  		= s[4]
		# self.Time				= float(s[5]/1000.0)
		# self.Counter		 	= s[6]
		# self.SerialNumber		= s[7]
		# self.NumberEntries		= s[8]

		# rec_fmt 				= '=HHhhhH'
		# rec_len 				= struct.calcsize(rec_fmt)
		# rec_unpack 				= struct.Struct(rec_fmt).unpack

		# # we need to store all the attitude data in a list
		# self.Attitude = [0 for i in range(self.NumberEntries)]

		# i = 0
		# while i < self.NumberEntries:
		# 	data = self.fileptr.read(rec_len)
		# 	s = rec_unpack(data)
		# 	# date, time,status,roll,pitch,heave,heading
		# 	self.Attitude[i] = [self.RecordDate, self.Time + float (s[0]/1000.0), s[1], s[2]/100.0, s[3]/100.0, s[4]/100.0, s[5]/100.0]
		# 	i = i + 1

		# rec_fmt 	= '=BBH'
		# rec_len 	= struct.calcsize(rec_fmt)
		# rec_unpack 	= struct.Struct(rec_fmt).unpack_from
		# data = self.fileptr.read(rec_len)
		# s = rec_unpack(data)

		# self.systemDescriptor  	= s[0]
		# self.ETX				= s[1]
		# self.checksum			= s[2]

###############################################################################
class CLOCK:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram 	= '#SCL'
		self.offset 			= fileptr.tell()
		self.numberofbytes 		= numberofbytes
		self.fileptr 			= fileptr
		self.data 				= ""
		self.fileptr.seek(numberofbytes, 1)

	def read(self):
		self.fileptr.seek(self.offset, 0)
		rec_fmt = kmallreader.EMdgmHeader_def  + kmallreader.EMdgmScommon_def + kmallreader.EMdgmSCLdataFromSensor_def
		rec_len 	= struct.calcsize(rec_fmt)
		rec_unpack 	= struct.Struct(rec_fmt).unpack
		# bytesRead = rec_len
		s = rec_unpack(self.fileptr.read(rec_len))

		decodeheader(s, self)

		self.numbytescmnpart	= s[7]
		self.sensorsystem		= s[8]
		self.sensorstatus		= s[9]
		self.padding			= s[10]

		self.clockoffset		= s[11]
		self.clockDevPU_nanosec	= s[12]
		self.dataFromSensor 	= s[13]

		# reset the file pointer to the end of teh packet.  for some reasdon we are 4 bytes out??? pkpk
		self.fileptr.seek(self.offset + self.numberofbytes, 0)

###############################################################################
class IIP_INSTALLATION:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram = '#IIP'	# assign the KM code for this datagram type
		self.offset = fileptr.tell()	# remember where this packet resides in the file so we can return if needed
		self.numberofbytes = numberofbytes			  # remember how many bytes this packet contains. This includes the first 4 bytes represnting the number of bytes inthe datagram
		self.fileptr = fileptr		  # remember the file pointer so we do not need to pass from the host process
		self.fileptr.seek(numberofbytes, 1)	 # move the file pointer to the end of the record so we can skip as the default actions
		self.data = ""

	def read(self):
		self.fileptr.seek(self.offset, 0)# move the file pointer to the start of the record so we can read from disc

		rec_fmt = kmallreader.EMdgmHeader_def  + "H"
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		# read the record from disc
		bytesread = rec_len
		s = rec_unpack(self.fileptr.read(rec_len))

		decodeheader(s, self)

		# self.numberofbytes		= s[0]
		# self.typeofdatagram		= s[1].decode('utf-8').rstrip('\x00')
		# self.version			= s[2]
		# self.systemid			= s[3]
		# self.echosounderid		= s[4]
		# self.time_sec			= s[5]
		# self.time_nanosec		= s[6]
		# self.date 				= from_timestamp(self.time_sec + self.time_nanosec/1000000000)
		self.numBytesCmnPart	= s[7]
		# self.info  				= s[8]
		# self.status		 		= s[9]
		# self.install_txt		= s[10]

		# totalAsciiBytes = self.numberofbytes - rec_len # we do not need to read the header twice
		self.txt = self.fileptr.read(self.numBytesCmnPart)# read the record from disc
		bytesread = bytesread + self.numBytesCmnPart
		self.installationparameters = self.txt.decode('utf-8', errors="ignore")
		# parameters = re.split(';\n',parameters)
		# self.installationParameters = {}
		# # for p in parameters:
		# parts = re.split(',',parameters) ; 
		# for p in parts:
		# 	p = p.replace("\n","")
		# 	print (p)
		# 	if len(p) > 1:
		# 		self.installationParameters[parts[0]] = parts[1].strip()

		#read any trailing bytes.  We have seen the need for this with some .all files.
		if bytesread < self.numberofbytes:
			self.fileptr.read(int(self.numberofbytes - bytesread))

###############################################################################
class RANGEDEPTH:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram = '#MRZ'	# assign the KM code for this datagram type
		self.offset = fileptr.tell()	# remember where this packet resides in the file so we can return if needed
		self.numberofbytes = numberofbytes			  # remember how many bytes this packet contains
		self.fileptr = fileptr		  # remember the file pointer so we do not need to pass from the host process
		self.fileptr.seek(numberofbytes, 1)	 # move the file pointer to the end of the record so we can skip as the default actions
		self.data = ""

	def read(self, headeronly=False):
		self.fileptr.seek(self.offset, 0)# move the file pointer to the start of the record so we can read from disc
		rec_fmt = kmallreader.EMdgmHeader_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))
		decodeheader(s, self)

		rec_fmt = kmallreader.EMdgmMpartition_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))
		self.numOfDgms 				= s[0]
		self.dgmNum 				= s[1]

		EMdgmMbody_def				= "=2h8B"
		rec_fmt = EMdgmMbody_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))
		self.numBytesCmnPart 		= s[0]
		self.pingCnt 				= s[1]
		self.rxFansPerPing 			= s[2]
		self.rxFanIndex 			= s[3]
		self.swathsPerPing 			= s[4]
		self.swathAlongPosition 	= s[5]
		self.txTransducerInd 		= s[6]
		self.rxTransducerInd 		= s[7]
		self.numRxTransducers 		= s[8]
		self.algorithmType 			= s[9]


		EMdgmMRZ_pingInfo_def = "=2Hf6BH11f2H2BHL3f2Hf 2H 6f4B 2df"
		rec_fmt = EMdgmMRZ_pingInfo_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))

		self.numBytesInfoData							= s[0]
		self.padding0									= s[1]
 
		# Ping info
		self.pingRate_Hz								= s[2]
		self.beamSpacing								= s[3]
		self.depthMode									= s[4]
		self.subDepthMode								= s[5]
		self.distanceBtwSwath							= s[6]
		self.detectionMode								= s[7]
		self.pulseForm									= s[8]
		self.padding1									= s[9]
		self.frequencyMode_Hz							= s[10]
		self.freqRangeLowLim_Hz							= s[11]
		self.freqRangeHighLim_Hz						= s[12]
		self.maxTotalTxPulseLength_sec					= s[13]
		self.maxEffTxPulseLength_sec					= s[14]
		self.maxEffTxBandWidth_Hz						= s[15]
		self.absCoeff_dBPerkm							= s[16]
		self.portSectorEdge_deg							= s[17]
		self.starbSectorEdge_deg						= s[18]
		self.portMeanCov_deg							= s[19]
		self.starbMeanCov_deg							= s[20]
		self.portMeanCov_m								= s[21]
		self.starbMeanCov_m								= s[22]
		self.modeAndStabilisation						= s[23]
		self.runtimeFilter1								= s[24]
		self.runtimeFilter2								= s[25]
		self.pipeTrackingStatus							= s[26]
		self.transmitArraySizeUsed_deg					= s[27]
		self.receiveArraySizeUsed_deg					= s[28]
		self.transmitPower_dB							= s[29]
		self.SLrampUpTimeRemaining						= s[30]
		self.padding2									= s[31]
		self.yawAngle_deg								= s[32]
		# Info of tx sector data block, EMdgmMRZ_txSectorInfo
		self.numTxSectors								= s[33]
		self.numBytesPerTxSector						= s[34]
 
		# Info at time of midpoint of first tx pulse
		self.headingVessel_deg							= s[35]
		self.heading									= s[35]
		self.soundSpeedAtTxDepth_mPerSec				= s[36]
		self.txTransducerDepth_m						= s[37]
		self.z_waterLevelReRefPoint_m					= s[38]
		self.x_kmallToall_m								= s[39]
		self.y_kmallToall_m								= s[40]
		self.latLongInfo								= s[41]
		self.posSensorStatus							= s[42]
		self.attitudeSensorStatus						= s[43]
		self.padding3									= s[44]
		self.latitude_deg								= s[45]
		self.latitude									= s[45]
		self.longitude_deg								= s[46]
		self.longitude									= s[46]
		self.ellipsoidHeightReRefPoint_m				= s[47]

		if headeronly:
			# reset the file pointer to the end of the packet.  for some reasdon we are 4 bytes out??? pkpk
			self.fileptr.seek(self.offset + self.numberofbytes, 0)
			return

		for i in range(self.numTxSectors):
			EMdgmMRZ_txSectorInfo_def = "=4B7f2BH"
			rec_fmt = EMdgmMRZ_txSectorInfo_def
			rec_len = struct.calcsize(rec_fmt)
			rec_unpack = struct.Struct(rec_fmt).unpack
			s = rec_unpack(self.fileptr.read(rec_len))

			self.txSectorNumb			= s[0]
			self.txArrNumber			= s[1]
			self.txSubArray				= s[2]
			self.padding0				= s[3]
			self.sectorTransmitDelay_sec= s[4]
			self.tiltAngleReTx_deg		= s[5]
			self.txNominalSourceLevel_dB= s[6]
			self.txFocusRange_m			= s[7]
			self.centreFreq_Hz			= s[8]
			self.signalBandWidth_Hz		= s[9]
			self.totalSignalLength_sec	= s[10]
			self.pulseShading			= s[11]
			self.signalWaveForm			= s[12]
			self.padding1				= s[13]


		# receiver speific information for this swath
		EMdgmMRZ_rxInfo_def = "4H4f4H"
		rec_fmt = EMdgmMRZ_rxInfo_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))

		self.numBytesRxInfo				= s[0]
		self.numSoundingsMaxMain		= s[1] # number of beams to process
		self.numSoundingsValidMain		= s[2]
		self.numBytesPerSounding		= s[3]
		self.WCSampleRate				= s[4]
		self.seabedImageSampleRate		= s[5]
		self.BSnormal_dB				= s[6]
		self.BSoblique_dB				= s[7]
		self.extraDetectionAlarmFlag	= s[8]
		self.numExtraDetections			= s[9]
		self.numExtraDetectionClasses	= s[10]
		self.numBytesPerClass			= s[11]

		for i in range(self.numExtraDetections):
			EMdgmMRZ_extraDetClassInfo_def = "HbB"
			rec_fmt = EMdgmMRZ_extraDetClassInfo_def
			rec_len = struct.calcsize(rec_fmt)
			rec_unpack = struct.Struct(rec_fmt).unpack
			s = rec_unpack(self.fileptr.read(rec_len))

			self.numExtraDetInClass 	= s[0]
			self.padding 				= s[1]
			self.alarmFlag 				= s[2]

		# DECODE THE SOUNDINGS
		# Data for each sounding, e.g. XYZ, reflectivity, two way travel time etc.
		EMdgmMRZ_sounding_def = "HB 7BH6f 2Hf 4f 7f 6fH 3H"
		rec_fmt = EMdgmMRZ_sounding_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack

		beams = []
		timestamp = to_timestamp(self.date)
		for i in range(self.numSoundingsMaxMain):
			s = rec_unpack(self.fileptr.read(rec_len))
			beam = cBeam(timestamp, s)
			beams.append(beam)

		self.beams = beams
		# DECODE SIDESCAN INTENSITY
		SInumsamples = sum(beam.SInumSamples for beam in beams)
		SIsample_desidB = "%sh" % (SInumsamples)
		# SIsample_desidB = "%sh" % (kmallreader.MAX_SIDESCAN_SAMP)
		rec_fmt = SIsample_desidB
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))

		self.SInumSamples 					= SInumsamples # s[0]

		# reset the file pointer to the end of the packet.  for some reasdon we are 4 bytes out??? pkpk
		self.fileptr.seek(self.offset + self.numberofbytes, 0)

###############################################################################
class POSITION:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram = '#SPO'	# assign the KM code for this datagram type
		self.offset = fileptr.tell()	# remember where this packet resides in the file so we can return if needed
		self.numberofbytes = numberofbytes			  # remember how many bytes this packet contains
		self.fileptr = fileptr		  # remember the file pointer so we do not need to pass from the host process
		self.fileptr.seek(numberofbytes, 1)	 # move the file pointer to the end of the record so we can skip as the default actions
		self.data = ""

	def read(self):
		self.fileptr.seek(self.offset, 0)# move the file pointer to the start of the record so we can read from disc
		rec_fmt = kmallreader.EMdgmHeader_def +  kmallreader.EMdgmScommon_def
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))

		decodeheader(s, self)

		self.numBytesCmnPart = s[7]
		self.sensorSystem = s[8]
		self.sensorStatus = s[9]
		self.padding = s[10]

		rec_fmt = kmallreader.EMdgmSPOdataBlock_def

		sensorrawbytes = self.numberofbytes - struct.calcsize(kmallreader.EMdgmHeader_def) - struct.calcsize(kmallreader.EMdgmScommon_def) - struct.calcsize(kmallreader.EMdgmSPOdataBlock_def)
		rec_fmt = rec_fmt + "%ss" % (int(sensorrawbytes))
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))

		self.timeFromSensor_sec 				= s[0]
		self.timeFromSensor_nanosec 			= s[1]
		self.posFixQuality_m 					= s[2]
		self.correctedLat_deg 					= s[3]
		self.latitude		 					= s[3]
		self.correctedLong_deg 					= s[4]
		self.longitude		 					= s[4]
		self.speedOverGround_mPerSec 			= s[5]
		self.courseOverGround_deg 				= s[6]
		self.heading			 				= s[6]
		self.ellipsoidHeightReRefPoint_m 		= s[7]
		self.posDataFromSensor 					= s[8]
		# print(self.posDataFromSensor)

		# reset the file pointer to the end of teh packet.  for some reasdon we are 4 bytes out??? pkpk
		self.fileptr.seek(self.offset + self.numberofbytes, 0)

###############################################################################
class IOP_RUNTIME:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram = '#IOP'	# assign the KM code for this datagram type
		self.offset = fileptr.tell()	# remember where this packet resides in the file so we can return if needed
		self.numberofbytes = numberofbytes			  # remember how many bytes this packet contains
		self.fileptr = fileptr		  # remember the file pointer so we do not need to pass from the host process
		self.fileptr.seek(numberofbytes, 1)	 # move the file pointer to the end of the record so we can skip as the default actions
		self.data = ""

	###############################################################################
	def read(self):
		self.fileptr.seek(self.offset, 0)# move the file pointer to the start of the record so we can read from disc
		rec_fmt = kmallreader.EMdgmHeader_def  + "H"
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		# read the record from disc
		bytesRead = rec_len
		s = rec_unpack(self.fileptr.read(rec_len))

		decodeheader(s, self)
		self.numBytesCmnPart	= s[7]

		# totalAsciiBytes = self.numberofbytes - rec_len # we do not need to read the header twice
		self.txt = self.fileptr.read(self.numBytesCmnPart)# read the record from disc
		bytesRead = bytesRead + self.numBytesCmnPart
		self.runtimeparameters = self.txt.decode('utf-8', errors="ignore")

		# reset the file pointer to the end of teh packet.  for some reasdon we are 4 bytes out??? pkpk
		self.fileptr.seek(self.offset + self.numberofbytes, 0)

		# parameters = re.split(';\n',parameters)
		# self.installationParameters = {}
		# # for p in parameters:
		# parts = re.split(',',parameters) ; 
		# for p in parts:
		# 	p = p.replace("\n","")
		# 	print (p)
		# 	if len(p) > 1:
		# 		self.installationParameters[parts[0]] = parts[1].strip()

		#read any trailing bytes.  We have seen the need for this with some .all files.
		# if bytesRead < self.numberofbytes:
		# 	self.fileptr.read(int(self.numberofbytes - bytesRead))

	# def read(self):
	# 	self.fileptr.seek(self.offset, 0)# move the file pointer to the start of the record so we can read from disc
	# 	rec_fmt = kmallreader.EMdgmHeader_def  + "H"

	# 	rec_fmt = '=LBBHLLHHBBBBBBHHHHHbBBBBBHBBBBHHBBH'
	# 	rec_len = struct.calcsize(rec_fmt)
	# 	rec_unpack = struct.Struct(rec_fmt).unpack
	# 	data = self.fileptr.read(rec_len)
	# 	s = rec_unpack(data)

	# 	# self.numberofbytes= s[0]
	# 	self.STX			 				= s[1]
	# 	self.typeofdatagram  				= chr(s[2])
	# 	self.EMModel		 				= s[3]
	# 	self.RecordDate	  					= s[4]
	# 	self.Time							= s[5]/1000
	# 	self.Counter		 				= s[6]
	# 	self.SerialNumber					= s[7]

	# 	self.operatorStationStatus 			= s[8]
	# 	self.processingUnitStatus			= s[9]
	# 	self.BSPStatus			  			= s[10]
	# 	self.sonarHeadStatus				= s[11]
	# 	self.mode							= s[12]
	# 	self.filterIdentifier				= s[13]
	# 	self.minimumDepth					= s[14]
	# 	self.maximumDepth					= s[15]
	# 	self.absorptionCoefficient  		= s[16]/100
	# 	self.transmitPulseLength			= s[17]
	# 	self.transmitBeamWidth	  			= s[18]
	# 	self.transmitPower		  			= s[19]
	# 	self.receiveBeamWidth				= s[20]
	# 	self.receiveBandwidth				= s[21]
	# 	self.mode2				  			= s[22]
	# 	self.tvg							= s[23]
	# 	self.sourceOfSpeedSound	 			= s[24]
	# 	self.maximumPortWidth				= s[25]
	# 	self.beamSpacing					= s[26]
	# 	self.maximumPortCoverageDegrees	 	= s[27]
	# 	self.yawMode						= s[28]
	# 	# self.yawAndPitchStabilisationMode= s[28]
	# 	self.maximumStbdCoverageDegrees	 	= s[29]
	# 	self.maximumStbdWidth				= s[30]
	# 	self.transmitAAlongTilt			 	= s[31]
	# 	self.filterIdentifier2				= s[32]
	# 	self.ETX							= s[33]
	# 	self.checksum						= s[34]

	# 	self.beamSpacingString = "Determined by beamwidth"
	# 	if (isBitSet(self.beamSpacing, 0)):
	# 		self.beamSpacingString = "Equidistant"
	# 	if (isBitSet(self.beamSpacing, 1)):
	# 		self.beamSpacingString = "Equiangular"
	# 	if (isBitSet(self.beamSpacing, 0) and isBitSet(self.beamSpacing, 1)):
	# 		self.beamSpacingString = "High density equidistant"
	# 	if (isBitSet(self.beamSpacing, 7)):
	# 		self.beamSpacingString = self.beamSpacingString + "+Two Heads"

	# 	self.yawAndPitchStabilisationMode= "Yaw stabilised OFF"
	# 	if (isBitSet(self.yawMode, 0)):
	# 		self.yawAndPitchStabilisationMode = "Yaw stabilised ON"
	# 	if (isBitSet(self.yawMode, 1)):
	# 		self.yawAndPitchStabilisationMode = "Yaw stabilised ON"
	# 	if (isBitSet(self.yawMode, 1) and isBitSet(self.yawMode, 0)):
	# 		self.yawAndPitchStabilisationMode = "Yaw stabilised ON (manual)"
	# 	if (isBitSet(self.yawMode, 7)):
	# 		self.yawAndPitchStabilisationMode = self.yawAndPitchStabilisationMode + "+Pitch stabilised ON"

	# 	self.DepthMode = "VeryShallow"
	# 	if (isBitSet(self.mode, 0)):
	# 		self.DepthMode = "Shallow"
	# 	if (isBitSet(self.mode, 1)):
	# 		self.DepthMode = "Medium"
	# 	if (isBitSet(self.mode, 0) & (isBitSet(self.mode, 1))):
	# 		self.DepthMode = "VeryDeep"
	# 	if (isBitSet(self.mode, 2)):
	# 		self.DepthMode = "VeryDeep"
	# 	if (isBitSet(self.mode, 0) & (isBitSet(self.mode, 2))):
	# 		self.DepthMode = "VeryDeep"

	# 	if str(self.EMModel) in 'EM2040, EM2045':
	# 		self.DepthMode = "200kHz"
	# 		if (isBitSet(self.mode, 0)):
	# 			self.DepthMode = "300kHz"
	# 		if (isBitSet(self.mode, 1)):
	# 			self.DepthMode = "400kHz"

	# 	self.TXPulseForm = "CW"
	# 	if (isBitSet(self.mode, 4)):
	# 		self.TXPulseForm = "Mixed"
	# 	if (isBitSet(self.mode, 5)):
	# 		self.TXPulseForm = "FM"

	# 	self.dualSwathMode = "Off"
	# 	if (isBitSet(self.mode, 6)):
	# 		self.dualSwathMode = "Fixed"
	# 	if (isBitSet(self.mode, 7)):
	# 		self.dualSwathMode = "Dynamic"

	# 	self.filterSetting = "SpikeFilterOff"
	# 	if (isBitSet(self.filterIdentifier, 0)):
	# 		self.filterSetting = "SpikeFilterWeak"
	# 	if (isBitSet(self.filterIdentifier, 1)):
	# 		self.filterSetting = "SpikeFilterMedium"
	# 	if (isBitSet(self.filterIdentifier, 0) & (isBitSet(self.filterIdentifier, 1))):
	# 		self.filterSetting = "SpikeFilterMedium"
	# 	if (isBitSet(self.filterIdentifier, 2)):
	# 		self.filterSetting += "+SlopeOn"
	# 	if (isBitSet(self.filterIdentifier, 3)):
	# 		self.filterSetting += "+SectorTrackingOn"
	# 	if ((not isBitSet(self.filterIdentifier, 4)) & (not isBitSet(self.filterIdentifier, 7))):
	# 		self.filterSetting += "+RangeGatesNormal"
	# 	if ((isBitSet(self.filterIdentifier, 4)) & (not isBitSet(self.filterIdentifier, 7))):
	# 		self.filterSetting += "+RangeGatesLarge"
	# 	if ((not isBitSet(self.filterIdentifier, 4)) & (isBitSet(self.filterIdentifier, 7))):
	# 		self.filterSetting += "+RangeGatesSmall"
	# 	if (isBitSet(self.filterIdentifier, 5)):
	# 		self.filterSetting += "+AerationFilterOn"
	# 	if (isBitSet(self.filterIdentifier, 6)):
	# 		self.filterSetting += "+InterferenceFilterOn"

	# def header(self):
	# 	header = ""
	# 	header += "typeofdatagram,"
	# 	header += "EMModel,"
	# 	header += "RecordDate,"
	# 	header += "Time,"
	# 	header += "Counter,"
	# 	header += "SerialNumber,"
	# 	header += "operatorStationStatus,"
	# 	header += "processingUnitStatus,"
	# 	header += "BSPStatus,"
	# 	header += "sonarHeadStatus,"
	# 	header += "mode,"
	# 	header += "dualSwathMode,"
	# 	header += "TXPulseForm,"
	# 	header += "filterIdentifier,"
	# 	header += "filterSetting,"
	# 	header += "minimumDepth,"
	# 	header += "maximumDepth,"
	# 	header += "absorptionCoefficient,"
	# 	header += "transmitPulseLength,"
	# 	header += "transmitBeamWidth,"
	# 	header += "transmitPower,"
	# 	header += "receiveBeamWidth,"
	# 	header += "receiveBandwidth,"
	# 	header += "mode2,"
	# 	header += "tvg,"
	# 	header += "sourceOfSpeedSound,"
	# 	header += "maximumPortWidth,"
	# 	header += "beamSpacing,"
	# 	header += "maximumPortCoverageDegrees,"
	# 	header += "yawMode,"
	# 	header += "yawAndPitchStabilisationMode,"
	# 	header += "maximumStbdCoverageDegrees,"
	# 	header += "maximumStbdWidth,"
	# 	header += "transmitAAlongTilt,"
	# 	header += "filterIdentifier2,"
	# 	return header

	# def parameters(self):
	# 	'''this function returns the runtime record in a human readmable format.  there are 2 strings returned, teh header which changes with every record and the paramters which only change when the user changes a setting.  this means we can reduce duplicate records by testing the parameters string for changes'''
	# 	s = '%s,%d,' %(self.operatorStationStatus, self.processingUnitStatus)
	# 	s += '%d,%d,' %(self.BSPStatus, self.sonarHeadStatus)
	# 	s += '%d,%s,%s,%d,%s,' %(self.mode, self.dualSwathMode, self.TXPulseForm, self.filterIdentifier, self.filterSetting)
	# 	s += '%.3f,%.3f,' %(self.minimumDepth, self.maximumDepth)
	# 	s += '%.3f,%.3f,' %(self.absorptionCoefficient, self.transmitPulseLength)
	# 	s += '%.3f,%.3f,' %(self.transmitBeamWidth, self.transmitPower)
	# 	s += '%.3f,%.3f,' %(self.receiveBeamWidth, self.receiveBandwidth)
	# 	s += '%d,%.3f,' %(self.mode2, self.tvg)
	# 	s += '%d,%d,' %(self.sourceOfSpeedSound, self.maximumPortWidth)
	# 	s += '%.3f,%d,' %(self.beamSpacing, self.maximumPortCoverageDegrees)
	# 	s += '%s,%s,%d,' %(self.yawMode, self.yawAndPitchStabilisationMode, self.maximumStbdCoverageDegrees)
	# 	s += '%d,%d,' %(self.maximumStbdWidth, self.transmitAAlongTilt)
	# 	s += '%s' %(self.filterIdentifier2)
	# 	return s

	# def __str__(self):
	# 	'''this function returns the runtime record in a human readmable format.  there are 2 strings returned, teh header which changes with every record and the paramters which only change when the user changes a setting.  this means we can reduce duplicate records by testing the parameters string for changes'''
	# 	s = '%s,%d,' %(self.typeofdatagram, self.EMModel)
	# 	s += '%s,%.3f,' %(self.RecordDate, self.Time)
	# 	s += '%d,%d,' %(self.Counter, self.SerialNumber)
	# 	s += '%s,%d,' %(self.operatorStationStatus, self.processingUnitStatus)
	# 	s += '%d,%d,' %(self.BSPStatus, self.sonarHeadStatus)
	# 	s += '%d,%s,%s,%d,%s,' %(self.mode, self.dualSwathMode, self.TXPulseForm, self.filterIdentifier, self.filterSetting)
	# 	s += '%.3f,%.3f,' %(self.minimumDepth, self.maximumDepth)
	# 	s += '%.3f,%.3f,' %(self.absorptionCoefficient, self.transmitPulseLength)
	# 	s += '%.3f,%.3f,' %(self.transmitBeamWidth, self.transmitPower)
	# 	s += '%.3f,%.3f,' %(self.receiveBeamWidth, self.receiveBandwidth)
	# 	s += '%d,%.3f,' %(self.mode2, self.tvg)
	# 	s += '%d,%d,' %(self.sourceOfSpeedSound, self.maximumPortWidth)
	# 	s += '%.3f,%d,' %(self.beamSpacing, self.maximumPortCoverageDegrees)
	# 	s += '%s,%s,%d,' %(self.yawMode, self.yawAndPitchStabilisationMode, self.maximumStbdCoverageDegrees)
	# 	s += '%d,%d,' %(self.maximumStbdWidth, self.transmitAAlongTilt)
	# 	s += '%s' %(self.filterIdentifier2)
	# 	return s

		# return pprint.pformat(vars(self))

###############################################################################
class UNKNOWN_RECORD:
	'''used as a convenience tool for datagrams we have no bespoke classes.  Better to make a bespoke class'''
	def __init__(self, fileptr, numberofbytes, typeofdatagram):
		self.typeofdatagram = typeofdatagram
		self.offset = fileptr.tell()
		self.numberofbytes = numberofbytes
		self.fileptr = fileptr
		self.fileptr.seek(numberofbytes, 1)
		self.data = ""
	def read(self):
		self.data = self.fileptr.read(self.numberofbytes)

###############################################################################
class SVP:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram = '#SVP'
		self.offset = fileptr.tell()
		self.numberofbytes = numberofbytes
		self.fileptr = fileptr
		self.fileptr.seek(numberofbytes, 1)
		self.data = []

	def read(self):
		self.fileptr.seek(self.offset, 0)
		rec_fmt = kmallreader.EMdgmHeader_def + "HH4sLdd" 
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack_from
		s = rec_unpack(self.fileptr.read(rec_len))

		decodeheader(s, self)
		# self.numberofbytes		= s[0]
		# self.typeofdatagram		= s[1].decode('utf-8').rstrip('\x00')
		# self.version			= s[2]
		# self.systemid			= s[3]
		# self.echosounderid		= s[4]
		# self.time_sec			= s[5]
		# self.time_nanosec		= s[6]
		# self.date 				= from_timestamp(self.time_sec + self.time_nanosec/1000000000)

		self.numBytesCmnPart	= s[7]
		self.numSamples			= s[8]
		self.sensorFormat		= s[9]
		self.time_sec			= s[10]
		self.latitude_deg		= s[11]
		self.longitude_deg		= s[12]

		# now read the SVP profile details... 
		rec_fmt = "ffLff"
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		# i = 0
		for i in range (self.numSamples):
			data = self.fileptr.read(rec_len)
			s = rec_unpack(data)
			self.data.append(s)

		# reset the file pointer to the end of teh packet.  for some reasdon we are 4 bytes out??? pkpk
		self.fileptr.seek(self.offset + self.numberofbytes, 0)


###############################################################################
# TIME HELPER FUNCTIONS
###############################################################################
def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()

def to_DateTime(recordDate, recordTime):
	'''return a python date object from a split date and time record. works with kongsberg date and time structures'''
	date_object = datetime.strptime(str(recordDate), '%Y%m%d') + timedelta(0,recordTime)
	return date_object

def from_timestamp(unixtime):
	return datetime.utcfromtimestamp(unixtime)

def dateToKongsbergDate(dateObject):
	return dateObject.strftime('%Y%m%d')

def dateToKongsbergTime(dateObject):
	return dateObject.strftime('%H%M%S')

def dateToSecondsSinceMidnight(dateObject):
	return (dateObject - dateObject.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

###############################################################################
# bitwise helper functions
###############################################################################
def isBitSet(int_type, offset):
	'''testBit() returns a nonzero result, 2**offset, if the bit at 'offset' is one.'''
	mask = 1 << offset
	return (int_type & (1 << offset)) != 0

def set_bit(value, bit):
 return value | (1<<bit)

if __name__ == "__main__":
		main()
		# exit()


################################################################################
# /*h+*/
#  #ifndef _EMDGMFORMAT_H
#  #define _EMDGMFORMAT_H
 
#  #include "stdint.h"
 
#  #ifndef _VXW
#  #pragma pack(4)
#  #endif
 
#  /*
 
#    Revision History:
 
#    01  01 SEP 2016  Rev A.
#    02  01 MAR 2017  Rev B.
#    03  05 JUL 2017  Rev C.
#    04  08 DES 2017  Rev D.
#    05  25 MAY 2018  Rev E.
#    06  16 NOV 2018  Rev F
#   */
  
#  #define EM_DGM_FORMAT_VERSION "Rev F 2018-11-16" 
#  #define MAX_NUM_BEAMS 1024 
#  #define MAX_EXTRA_DET 1024 
#  #define MAX_EXTRA_DET_CLASSES 11   
#  #define MAX_SIDESCAN_SAMP 60000   
#  #define MAX_SIDESCAN_EXTRA_SAMP 15000   
#  #define MAX_NUM_TX_PULSES 9  
#  #define MAX_ATT_SAMPLES  148 
#  #define MAX_SVP_POINTS 2000  
#  #define MAX_SVT_SAMPLES 1  
#  #define MAX_DGM_SIZE 64000  
#  #define MAX_NUM_MST_DGMS 256 
#  #define MAX_NUM_MWC_DGMS 256 
#  #define MAX_NUM_MRZ_DGMS 32  
#  #define MAX_SPO_DATALENGTH 250  
#  #define MAX_ATT_DATALENGTH 250  
#  #define MAX_SVT_DATALENGTH 64   
#  #define MAX_SCL_DATALENGTH 64   
#  #define MAX_SDE_DATALENGTH 32   
#  #define MAX_SHI_DATALENGTH 32   
#  #define MAX_CPO_DATALENGTH 250  
#  #define MAX_CHE_DATALENGTH 64   
#  #define UNAVAILABLE_POSFIX 0xffff 
#  #define UNAVAILABLE_LATITUDE 200.0f 
#  #define UNAVAILABLE_LONGITUDE 200.0f 
#  #define UNAVAILABLE_SPEED -1.0f 
#  #define UNAVAILABLE_COURSE -4.0f 
#  #define UNAVAILABLE_ELLIPSOIDHEIGHT -999.0f 
#  /*********************************************
#              Datagram names
#   *********************************************/
 
#  /* I - datagrams */
#  #define EM_DGM_I_INSTALLATION_PARAM        "#IIP"       
#  #define EM_DGM_I_OP_RUNTIME                "#IOP"       
 
#  /* S-datagrams */
#  #define EM_DGM_S_POSITION                  "#SPO"
#  #define EM_DGM_S_KM_BINARY                 "#SKM"
#  #define EM_DGM_S_SOUND_VELOCITY_PROFILE    "#SVP"
#  #define EM_DGM_S_SOUND_VELOCITY_TRANSDUCER "#SVT"
#  #define EM_DGM_S_CLOCK                     "#SCL"
#  #define EM_DGM_S_DEPTH                     "#SDE"
#  #define EM_DGM_S_HEIGHT                    "#SHI"
 
 
#  /* M-datagrams */
#  #define EM_DGM_M_RANGE_AND_DEPTH        "#MRZ"  
#  #define EM_DGM_M_WATER_COLUMN           "#MWC"
 
 
#  /* C-datagrams */
#  #define EM_DGM_C_POSITION         "#CPO"
#  #define EM_DGM_C_HEAVE            "#CHE"
 
#  /*********************************************
 
#     General datagram header        
 
#   *********************************************/
 
#  struct EMdgmHeader_def
#  {       
#          uint32_t numBytesDgm;           
#          uint8_t dgmType[4];                     
#          uint8_t dgmVersion;         
#          uint8_t systemID;                       
#          uint16_t echoSounderID;         
#          uint32_t time_sec;          
#          uint32_t time_nanosec;      
#  };
 
#  typedef struct EMdgmHeader_def EMdgmHeader, *pEMdgmHeader;
 
#  /********************************************* 
 
#     Sensor datagrams    
 
#   *********************************************/
 
#  struct EMdgmScommon_def
#  {
#          uint16_t numBytesCmnPart;  
#          uint16_t sensorSystem;     
#          uint16_t sensorStatus;     
#          uint16_t padding;
#  };
 
#  typedef struct EMdgmScommon_def EMdgmScommon, *pEMdgmScommon;
 
#  struct EMdgmSdataInfo_def
#  {
#          uint16_t numBytesInfoPart;  
#          uint16_t numSamplesArray;  
#          uint16_t numBytesPerSample;  
#          uint16_t numBytesRawSensorData; 
#  };
 
#  typedef struct EMdgmSdataInfo_def EMdgmSdataInfo, *pEMdgmSdataInfo;
 
 
#  /************************************
#     #SPO - Sensor Position data       
#   ************************************/
#  struct EMdgmSPOdataBlock_def
#  { 
#          uint32_t timeFromSensor_sec;            
#          uint32_t timeFromSensor_nanosec;            
#          float posFixQuality_m;  
#          double correctedLat_deg;   
#          double correctedLong_deg;   
#          float speedOverGround_mPerSec;  
#          float courseOverGround_deg;   
#          float ellipsoidHeightReRefPoint_m;  
#          int8_t posDataFromSensor[MAX_SPO_DATALENGTH]; 
#  };
 
#  typedef struct EMdgmSPOdataBlock_def EMdgmSPOdataBlock, *pEMdgmSPOdataBlock;
 
#  struct EMdgmSPO_def
#  {
#          struct EMdgmHeader_def header;
#          struct EMdgmScommon_def cmnPart;
#          struct EMdgmSPOdataBlock_def sensorData;
#  };
 
#  #define SPO_VERSION 0
#  typedef struct EMdgmSPO_def EMdgmSPO, *pEMdgmSPO;
 
 
#  /************************************
#     #SKM - KM binary sensor data       
#   ************************************/
#  struct EMdgmSKMinfo_def
#  {
#          uint16_t numBytesInfoPart;  
#          uint8_t sensorSystem;     
#          uint8_t sensorStatus;     
#          uint16_t sensorInputFormat;  
#          uint16_t numSamplesArray;  
#          uint16_t numBytesPerSample;  
#          uint16_t sensorDataContents; 
#  };
 
#  typedef struct EMdgmSKMinfo_def EMdgmSKMinfo, *pEMdgmSKMinfo;
#  struct KMbinary_def
#  {
#          uint8_t dgmType[4];                     
#          uint16_t numBytesDgm;           
#          uint16_t dgmVersion;         
#          uint32_t time_sec;       
#          uint32_t time_nanosec;   
#          uint32_t status;   
#          double latitude_deg;   
#          double longitude_deg;  
#          float ellipsoidHeight_m;  
#          float roll_deg;     
#          float pitch_deg;    
#          float heading_deg;  
#          float heave_m;  
#          float rollRate;  
#          float pitchRate;  
#          float yawRate;  
#          float velNorth; 
#          float velEast;  
#          float velDown;  
#          float latitudeError_m;   
#          float longitudeError_m;   
#          float ellipsoidHeightError_m;   
#          float rollError_deg;     
#          float pitchError_deg;   
#          float headingError_deg;  
#          float heaveError_m;   
#          float northAcceleration;   
#          float eastAcceleration;    
#          float downAcceleration;    
#  };
 
#  typedef struct KMbinary_def KMbinary, *pKMbinary;
 
#  struct KMdelayedHeave_def
#  {
#          uint32_t time_sec;
#          uint32_t time_nanosec;
#          float delayedHeave_m;  
#  };
#  typedef struct KMdelayedHeave_def KMdelayedHeave, *pKMdelayedHeave;
 
#  struct EMdgmSKMsample_def
#  {
#          struct KMbinary_def KMdefault;
#          struct KMdelayedHeave_def delayedHeave;
#  };
 
#  typedef struct EMdgmSKMsample_def EMdgmSKMsample, *pEMdgmSKMsample;
 
#  struct EMdgmSKM_def
#  {
#          struct EMdgmHeader_def header;
#          struct EMdgmSKMinfo_def infoPart;       
#          struct EMdgmSKMsample_def sample[MAX_ATT_SAMPLES];
#  };
 
#  #define SKM_VERSION 1
#  typedef struct EMdgmSKM_def EMdgmSKM, *pEMdgmSKM;
 
 
#  /************************************
#      #SVP - Sound Velocity Profile       
#   ************************************/
#  struct EMdgmSVPpoint_def
#  {
#          float depth_m;  
#          float soundVelocity_mPerSec;  
#          uint32_t padding;  
#          float temp_C;     
#          float salinity; 
#  };
 
#  typedef struct EMdgmSVPpoint_def EMdgmSVPpoint, *pEMdgmSVPpoint;
 
#  struct EMdgmSVP_def
#  {
#          struct EMdgmHeader_def header;
#          uint16_t numBytesCmnPart;  
#          uint16_t numSamples;  
#          uint8_t sensorFormat[4];      
#          uint32_t time_sec;     
#          double latitude_deg;  
#          double longitude_deg; 
#          struct EMdgmSVPpoint_def sensorData[MAX_SVP_POINTS];  
#  };
 
#  #define SVP_VERSION 1
#  typedef struct EMdgmSVP_def EMdgmSVP, *pEMdgmSVP;
 
#  /************************************
#  * #SVT - Sensor sound Velocity measured at Transducer
#  ************************************/
#  struct EMdgmSVTinfo_def
#  {
#      uint16_t numBytesInfoPart;  
#      uint16_t sensorStatus;     
#      uint16_t sensorInputFormat;  
#      uint16_t numSamplesArray;  
#      uint16_t numBytesPerSample;  
#      uint16_t sensorDataContents; 
#      float filterTime_sec; 
#      float soundVelocity_mPerSec_offset; 
#  };
 
#  struct EMdgmSVTsample_def
#  {                        
#      uint32_t time_sec;           
#      uint32_t time_nanosec;       
#      float soundVelocity_mPerSec; 
#      float temp_C;   
#      float pressure_Pa;  
#      float salinity; 
#  };
 
#  typedef struct EMdgmSVTsample_def EMdgmSVTsample, *pEMdgmSVTsample;
 
#  struct EMdgmSVT_def
#  {
#      struct EMdgmHeader_def header;
#      struct EMdgmSVTinfo_def infoPart;
#      struct EMdgmSVTsample_def sensorData[MAX_SVT_SAMPLES];
#  };
 
#  #define SVT_VERSION 0
#  typedef struct EMdgmSVT_def EMdgmSVT, *pEMdgmSVT;
 
#  /************************************
#      #SCL - Sensor CLock datagram
#   ************************************/
#  struct EMdgmSCLdataFromSensor_def
#  {
#          float offset_sec;  
#          int32_t clockDevPU_nanosec;    
#          uint8_t dataFromSensor[MAX_SCL_DATALENGTH];   
#  };
 
#  typedef struct EMdgmSCLdataFromSensor_def EMdgmSCLdataFromSensor, *pEMdgmSCLdataFromSensor;
 
#  struct EMdgmSCL_def
#  {
#          struct EMdgmHeader_def header;
#          struct EMdgmScommon_def cmnPart;  
#          struct EMdgmSCLdataFromSensor_def sensData;
#  };
 
#  #define SCL_VERSION 0
#  typedef struct EMdgmSCL_def EMdgmSCL, *pEMdgmSCL;
 
 
#  /************************************
#      #SDE - Sensor Depth data       
#   ************************************/
#  struct EMdgmSDEdataFromSensor_def
#  {
#          float depthUsed_m;  
#          float offset;  
#          float scale;  
#          double latitude_deg;  
#          double longitude_deg; 
#          uint8_t dataFromSensor[MAX_SDE_DATALENGTH];  
#  };
 
#  typedef struct EMdgmSDEdataFromSensor_def EMdgmSDEdataFromSensor, *pEMdgmSDEdataFromSensor;
 
#  struct EMdgmSDE_def
#  {
#          struct EMdgmHeader_def header;
#          struct EMdgmScommon_def cmnPart;
#          struct EMdgmSDEdataFromSensor_def sensorData;
#  };
 
#  #define SDE_VERSION 0
#  typedef struct EMdgmSDE_def EMdgmSDE, *pEMdgmSDE;
 
#  /************************************
#      #SHI - Sensor Height data      
#   ************************************/
#  struct EMdgmSHIdataFromSensor_def
#  {
#          uint16_t sensorType;  
#          float heigthUsed_m;  
#          uint8_t dataFromSensor[MAX_SHI_DATALENGTH];  
#  };
 
#  typedef struct EMdgmSHIdataFromSensor_def EMdgmSHIdataFromSensor, *pEMdgmSHIdataFromSensor;
 
#  struct EMdgmSHI_def
#  {
#          struct EMdgmHeader_def  header;
#          struct EMdgmScommon_def cmnPart;
#          struct EMdgmSHIdataFromSensor_def sensData;
#  };
 
#  #define SHI_VERSION 0
#  typedef struct EMdgmSHI_def EMdgmSHI, *pEMdgmSHI;
 
 
#  /********************************************* 
 
#     Multibeam datagrams    
 
#   *********************************************/
#  struct EMdgmMpartition_def
#  {
#          uint16_t numOfDgms;   
#          uint16_t dgmNum;      
#  };
 
#  typedef struct EMdgmMpartition_def EMdgmMpartition, *pEMdgmMpartition;
 
#  struct EMdgmMbody_def
#  {
#          uint16_t numBytesCmnPart;    
#          uint16_t pingCnt;  
#          uint8_t rxFansPerPing;    
#          uint8_t rxFanIndex;       
#          uint8_t swathsPerPing;     
#          uint8_t swathAlongPosition;  
#          uint8_t txTransducerInd;   
#          uint8_t rxTransducerInd;   
#          uint8_t numRxTransducers;  
#          uint8_t algorithmType;  
#  };
 
#  typedef struct EMdgmMbody_def EMdgmMbody, *pEMdgmMbody;
 
#  /************************************
#      #MRZ - multibeam data for raw range, 
#      depth, reflectivity, seabed image(SI) etc.
#   ************************************/
#  struct EMdgmMRZ_pingInfo_def
#  {
#          uint16_t numBytesInfoData;   
#          uint16_t padding0;   
#          float pingRate_Hz;  
#          uint8_t beamSpacing;  
#          uint8_t depthMode;   
#          uint8_t subDepthMode;  
#          uint8_t distanceBtwSwath; 
#          uint8_t detectionMode;   
#          uint8_t pulseForm; 
#          uint16_t padding1;
 
#          float frequencyMode_Hz; 
#          float freqRangeLowLim_Hz;   
#          float freqRangeHighLim_Hz; 
#          float maxTotalTxPulseLength_sec; 
#          float maxEffTxPulseLength_sec; 
#          float maxEffTxBandWidth_Hz; 
#          float absCoeff_dBPerkm;  
#          float portSectorEdge_deg;  
#          float starbSectorEdge_deg; 
#          float portMeanCov_deg;  
#          float starbMeanCov_deg; 
#          int16_t portMeanCov_m;  
#          int16_t starbMeanCov_m; 
#          uint8_t modeAndStabilisation; 
#          uint8_t runtimeFilter1;  
#          uint16_t runtimeFilter2; 
#          uint32_t pipeTrackingStatus;  
#          float transmitArraySizeUsed_deg; 
#          float receiveArraySizeUsed_deg;  
#          float transmitPower_dB; 
#          uint16_t SLrampUpTimeRemaining; 
#          uint16_t padding2;  
#          float yawAngle_deg; 
#          uint16_t numTxSectors;  
#          uint16_t numBytesPerTxSector;  
#          float headingVessel_deg;  
#          float soundSpeedAtTxDepth_mPerSec; 
#          float txTransducerDepth_m; 
#          float z_waterLevelReRefPoint_m; 
#          float x_kmallToall_m;   
#          float y_kmallToall_m;   
#          uint8_t latLongInfo; 
#          uint8_t posSensorStatus; 
#          uint8_t attitudeSensorStatus; 
#          uint8_t padding3;  
#          double latitude_deg; 
#          double longitude_deg; 
#          float ellipsoidHeightReRefPoint_m; 
#          };
 
#  typedef struct EMdgmMRZ_pingInfo_def EMdgmMRZ_pingInfo, *pEMdgmMRZ_pingInfo;
 
#  struct EMdgmMRZ_txSectorInfo_def
#  {
#          uint8_t txSectorNumb;  
#          uint8_t txArrNumber;  
#          uint8_t txSubArray;  
#          uint8_t padding0;    
#          float sectorTransmitDelay_sec;  
#          float tiltAngleReTx_deg; 
#          float txNominalSourceLevel_dB;  
#          float txFocusRange_m; 
#          float centreFreq_Hz;  
#          float signalBandWidth_Hz;     
#          float totalSignalLength_sec;    
#          uint8_t pulseShading;   
#          uint8_t signalWaveForm; 
#          uint16_t padding1;      
#  };
 
#  typedef struct EMdgmMRZ_txSectorInfo_def EMdgmMRZ_txSectorInfo, *pEMdgmMRZ_txSectorInfo;
 
#  struct EMdgmMRZ_rxInfo_def
#  {
#          uint16_t numBytesRxInfo;    
#          uint16_t numSoundingsMaxMain; 
#          uint16_t numSoundingsValidMain;  
#          uint16_t numBytesPerSounding; 
#          float WCSampleRate;   
#          float seabedImageSampleRate; 
#          float BSnormal_dB;  
#          float BSoblique_dB; 
#          uint16_t extraDetectionAlarmFlag;  
#          uint16_t numExtraDetections; 
#          uint16_t numExtraDetectionClasses; 
#          uint16_t numBytesPerClass;  
#  };
 
#  typedef struct EMdgmMRZ_rxInfo_def EMdgmMRZ_rxInfo, *pEMdgmMRZ_rxInfo;
 
#  struct EMdgmMRZ_extraDetClassInfo_def
#  {
#          uint16_t numExtraDetInClass;  
#          int8_t padding;  
#          uint8_t alarmFlag;  
#  };
 
#  typedef struct EMdgmMRZ_extraDetClassInfo_def EMdgmMRZ_extraDetClassInfo, *pEMdgmMRZ_extraDetClassInfo;
 
#  struct EMdgmMRZ_sounding_def
#  {
 
#          uint16_t soundingIndex; 
#          uint8_t txSectorNumb;  
#          uint8_t detectionType;   
#          uint8_t detectionMethod; 
#          uint8_t rejectionInfo1;  
#          uint8_t rejectionInfo2;  
#          uint8_t postProcessingInfo;  
#          uint8_t detectionClass; 
#          uint8_t detectionConfidenceLevel;  
#          uint16_t padding; 
#          float rangeFactor; 
#          float qualityFactor;  
#          float detectionUncertaintyVer_m;  
#          float detectionUncertaintyHor_m;  
#          float detectionWindowLength_sec;  
#          float echoLength_sec; 
#          uint16_t WCBeamNumb;       
#          uint16_t WCrange_samples;  
#          float WCNomBeamAngleAcross_deg; 
#          float meanAbsCoeff_dBPerkm; 
#          float reflectivity1_dB;  
#          float reflectivity2_dB;  
#          float receiverSensitivityApplied_dB; 
#          float sourceLevelApplied_dB; 
#          float BScalibration_dB; 
#          float TVG_dB; 
#          float beamAngleReRx_deg;  
#          float beamAngleCorrection_deg;  
#          float twoWayTravelTime_sec;  
#          float twoWayTravelTimeCorrection_sec; 
#          float deltaLatitude_deg;   
#          float deltaLongitude_deg;  
#          float z_reRefPoint_m; 
#          float y_reRefPoint_m; 
#          float x_reRefPoint_m; 
#          float beamIncAngleAdj_deg; 
#          uint16_t realTimeCleanInfo;     
#          uint16_t SIstartRange_samples; 
#          uint16_t SIcentreSample;  
#          uint16_t SInumSamples;    
#  };
 
#  typedef struct EMdgmMRZ_sounding_def EMdgmMRZ_sounding, *pEMdgmMRZ_sounding;
 
#  struct EMdgmMRZ_extraSI_def
#  {
 
#          uint16_t portStartRange_samples;  
#          uint16_t numPortSamples;           
#          int16_t portSIsample_desidB[MAX_SIDESCAN_EXTRA_SAMP]; 
#          uint16_t starbStartRange_samples; 
#          uint16_t numStarbSamples;   
#          int16_t starbSIsample_desidB[MAX_SIDESCAN_EXTRA_SAMP]; 
#  };
 
#  typedef struct EMdgmMRZ_extraSI_def EMdgmMRZ_extraSI, *pEMdgmMRZ_extraSI;
 
#  struct EMdgmMRZ_def
#  {
#          struct EMdgmHeader_def header;   
#          struct EMdgmMpartition_def partition;
#          struct EMdgmMbody_def cmnPart;
#          struct EMdgmMRZ_pingInfo_def pingInfo;                            
#          struct EMdgmMRZ_txSectorInfo_def sectorInfo[MAX_NUM_TX_PULSES];   
#          struct EMdgmMRZ_rxInfo_def rxInfo;                                
#          struct EMdgmMRZ_extraDetClassInfo_def extraDetClassInfo[MAX_EXTRA_DET_CLASSES];  
#          struct EMdgmMRZ_sounding_def sounding[MAX_NUM_BEAMS+MAX_EXTRA_DET];              
#          int16_t SIsample_desidB[MAX_SIDESCAN_SAMP];               
#  }; 
 
#  #define MRZ_VERSION 0
#  typedef struct EMdgmMRZ_def EMdgmMRZ, *pEMdgmMRZ;
 
#  /************************************
#      #MWC - water column datagram        
#   ************************************/
#  struct EMdgmMWCtxInfo_def
#  {
#          uint16_t numBytesTxInfo;  
#          uint16_t numTxSectors;  
#          uint16_t numBytesPerTxSector;   
#          int16_t padding;  
#          float heave_m; 
#  };
 
#  typedef struct EMdgmMWCtxInfo_def EMdgmMWCtxInfo, *pEMdgmMWCtxInfo;
 
#  struct EMdgmMWCtxSectorData_def
#  {
#          float tiltAngleReTx_deg;  
#          float centreFreq_Hz;        
#          float txBeamWidthAlong_deg; 
#          uint16_t txSectorNum;    
#          int16_t padding;  
#  };
 
#  typedef struct EMdgmMWCtxSectorData_def EMdgmMWCtxSectorData, *pEMdgmMWCtxSectorData;
 
#  struct EMdgmMWCrxInfo_def
#  {
#          uint16_t numBytesRxInfo;  
#          uint16_t numBeams;  
#          uint8_t numBytesPerBeamEntry;      
#          uint8_t phaseFlag;  
#          uint8_t TVGfunctionApplied;  
#          int8_t TVGoffset_dB; 
#          float sampleFreq_Hz;   
#          float soundVelocity_mPerSec;  
#  };
 
#  typedef struct EMdgmMWCrxInfo_def EMdgmMWCrxInfo, *pEMdgmMWCrxInfo;
 
#  struct EMdgmMWCrxBeamData_def
#  {
#          float beamPointAngReVertical_deg;
#          uint16_t startRangeSampleNum;
#          uint16_t detectedRangeInSamples;    
#          uint16_t beamTxSectorNum;
#          uint16_t numSampleData;  
#          int8_t  *sampleAmplitude05dB_p;  
#  };
 
#  typedef struct EMdgmMWCrxBeamData_def EMdgmMWCrxBeamData, *pEMdgmMWCrxBeamData;
 
#  struct EMdgmMWCrxBeamPhase1_def
#  {
#          int8_t rxBeamPhase; 
#  };
 
#  typedef struct EMdgmMWCrxBeamPhase1_def EMdgmMWCrxBeamPhase1, *pEMdgmMWCrxBeamPhase1;
 
#  struct EMdgmMWCrxBeamPhase2_def
#  {
#          int16_t rxBeamPhase; 
#  };
 
#  typedef struct EMdgmMWCrxBeamPhase2_def EMdgmMWCrxBeamPhase2, *pEMdgmMWCrxBeamPhase2;
 
#  struct EMdgmMWC_def
#  {
#          struct EMdgmHeader_def header;
#          struct EMdgmMpartition_def partition;
#          struct EMdgmMbody_def cmnPart;
#          struct EMdgmMWCtxInfo_def txInfo; 
#          struct EMdgmMWCtxSectorData_def sectorData[MAX_NUM_TX_PULSES]; 
#          struct EMdgmMWCrxInfo_def rxInfo;
#          struct EMdgmMWCrxBeamData_def *beamData_p; 
#  }; 
 
#  #define MWC_VERSION 0
#  typedef struct EMdgmMWC_def EMdgmMWC, *pEMdgmMWC;
 
 
 
 
#  /********************************************* 
 
#     Compatibility datagrams for .all to .kmall conversion support
 
#   *********************************************/
 
#  /************************************
#     #CPO - Compatibility position sensor data       
#   ************************************/
#  struct EMdgmCPOdataBlock_def
#  { 
#          uint32_t timeFromSensor_sec;            
#          uint32_t timeFromSensor_nanosec;            
#      float posFixQuality_m;  
#      double correctedLat_deg;   
#      double correctedLong_deg;   
#      float speedOverGround_mPerSec;  
#      float courseOverGround_deg;   
#      float ellipsoidHeightReRefPoint_m;  
#      int8_t posDataFromSensor[MAX_CPO_DATALENGTH]; 
#  };
 
#  typedef struct EMdgmCPOdataBlock_def EMdgmCPOdataBlock, *pEMdgmCPOdataBlock;
 
#  struct EMdgmCPO_def
#  {
#      struct EMdgmHeader_def header;
#      struct EMdgmScommon_def cmnPart;
#      struct EMdgmCPOdataBlock_def sensorData;
#  };
 
#  #define CPO_VERSION 0
#  typedef struct EMdgmCPO_def EMdgmCPO, *pEMdgmCPO;
 
 
#  /************************************
#      #CHE - Compatibility heave data      
#   ************************************/
#  struct EMdgmCHEdata_def
#  {
#      float heave_m;  
#  };
 
#  typedef struct EMdgmCHEdata_def EMdgmCHEdata, *pEMdgmCHEdata;
 
#  struct EMdgmCHE_def
#  {
#      struct EMdgmHeader_def  header;
#      struct EMdgmMbody_def cmnPart;
#      struct EMdgmCHEdata_def data;
#  };
 
#  #define CHE_VERSION 0
#  typedef struct EMdgmCHE_def EMdgmCHE, *pEMdgmCHE;
 
 
#  /********************************************* 
 
#     Installation and runtime datagrams    
 
#   *********************************************/
 
#  /************************************
#      #IIP - Info Installation PU     
#   ************************************/
#  struct EMdgmIIP_def
#  {
#          EMdgmHeader header;
#          uint16_t numBytesCmnPart;  
#          uint16_t info;                          
#          uint16_t status;                                
#          uint8_t install_txt;            
#  };
 
#  #define IIP_VERSION 0
#  typedef struct EMdgmIIP_def dgm_IIP, *pdgm_IIP;
 
 
#  /************************************
#      #IOP -  Runtime datagram  
#   ************************************/
#  struct EMdgmIOP_def
#  {
#          EMdgmHeader header;
#          uint16_t numBytesCmnPart;  
#          uint16_t info;                          
#          uint16_t status;                                
#          uint8_t runtime_txt;            
#  };
 
#  #define IOP_VERSION 0
#  typedef struct EMdgmIOP_def dgm_IOP, *pdgm_IOP;
 
 
#  /************************************
#      #IB - BIST Error Datagrams   
#   ************************************/
#  struct EMdgmIB_def 
#  {
#          EMdgmHeader header;
#          uint16_t numBytesCmnPart;  
#          uint8_t BISTInfo;         
#          uint8_t BISTStyle;        
#          uint8_t BISTNumber;       
#          int8_t  BISTStatus;       
#          uint8_t BISTText;         
#  };
 
#  #define BIST_VERSION 0
#  typedef struct EMdgmIB_def dgm_IB, *pdgm_IB;
 
#  #ifndef _VXW
#  #pragma pack()
#  #endif
#  #endif
