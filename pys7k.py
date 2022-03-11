#name:		  pfs7k
#created:	   May 2016
#by:			p.kennedy@fugro.com
#description:   python module to read an s7k sonar file
#notes:		 See main at end of script for example how to use this
#based on s7k version 34 21/2/2012
#version 2.00

# See readme.md for details

import pprint
import struct
import os.path
from datetime import datetime, timedelta
import geodetic
import numpy as np
import time
import os
import sys
# import cv2
import math
from argparse import ArgumentParser
from argparse import RawTextHelpFormatter
import os.path
from glob import glob
import fnmatch
import shapefile
import fileutils
from math import modf

def main():

	parser = ArgumentParser(description='Reads a s7k file.',
			epilog='Example: \n To process a single file use -i c:/temp/myfile.s7k \n to mass process every file in a folder use -i c:/temp/*.s7k\n To convert all files recursively in a folder, use -r -i c:/temp \n To convert all files recursively from the current folder, use -r -i ./*.s7k \n', formatter_class=RawTextHelpFormatter)
	parser.add_argument('-i', dest='inputfolder', action='store', help='The input folder to read')
	parser.add_argument('-r', action='store_true', default=False, dest='recursive', help='Search recursively.')
	parser.add_argument('-tl', action='store_true', default=True, dest='trackline', help='Create track polyline shapefile.')
	parser.add_argument('-o', dest='outputfile', action='store', default='trackplot.shp', help='Output filename to create. e.g. coverage.shp [Default: trackplot.shp]')
	parser.add_argument('-s', dest='step', action='store', default='10', help='Decimate the data to reduce the output size. [Default: 30]')

	# if len(sys.argv)==1:
	# 	parser.print_help()
	# 	sys.exit(1)

	args = parser.parse_args()


	if len(args.inputfolder) == 0:
		args.inputfolder = os.getcwd() + args.inputfolder

	if args.inputfolder == '.':
		args.inputfolder = os.getcwd() + args.inputfolder

	process(args)


###############################################################################
def process(args):
	matches = []
	fileCounter=0

	suffix = os.path.splitext(args.inputfolder)[1]
	matches = fileutils.findFiles2(True, args.inputfolder, "*.s7k")

	# if args.recursive:
	# 	for root, dirnames, filenames in os.walk(os.path.dirname(args.inputfolder)):
	# 		for f in fnmatch.filter(filenames, '*.s7k'):
	# 			matches.append(os.path.join(root, f))
	# 			# print (matches[-1])
	# else:
	# 	if os.path.exists(args.inputfolder):
	# 		matches.append (os.path.abspath(args.inputfolder))
	# 	else:
	# 		for filename in glob(args.inputfolder):
	# 			matches.append(filename)
	if len(matches) == 0:
		print ("Nothing found to convert, quitting")
		exit()
	# show the user there are some files to process...
	print (matches)
	fileCounter = len(matches)

	# fname, ext = os.path.splitext(os.path.expanduser(args.outputfile))
	# trackLineFileName = os.path.join(os.path.dirname(os.path.abspath(args.outputfile)), fname + "_trackLine.shp")

	# if args.trackline:
	# 	TLshp = createSHP(trackLineFileName, shapefile.POLYLINE)
	# 	if len(TLshp.fields) <= 1:
	# 		TLshp.field("LineName", "C")
	# 		TLshp.field("SurveyDate", "D")

	for filename in matches:
		#open the s7k file for reading by creating a new s7kReader class and passin in the filename to open.  The reader will read the initial header so we can get to grips with the file contents with ease.
		print ( "processing file:", filename)
		reader = s7kreader(filename)
		start_time = time.time() # time  the process

		# while reader.moreData():
		# 	typeofdatagram, datagram = reader.readDatagram()
		# 	print (typeofdatagram)


		print("Loading Navigation...")
		navigation = reader.loadNavigation(step=1)


		# create the track polyline
		# if args.trackline:
		# 	createTrackLine(reader, TLshp, float(args.step))

		# print the s7k file header information.  This gives a brief summary of the file contents.
		# for ch in range(reader.s7kFileHdr.NumberOfSonarChannels):
		# 	print(reader.s7kFileHdr.s7kChanInfo[ch])

		# while reader.moreData():
		# 	pingHdr = reader.readPacket()
		# 	if pingHdr != -999:
		# 		print (pingHdr.PingNumber,  pingHdr.SensorXcoordinate, pingHdr.SensorYcoordinate)

		# reader.rewind()
		# navigation = reader.loadNavigation()
		# for n in navigation:
		# 	print ("X: %.3f Y: %.3f Hdg: %.3f Alt: %.3f Depth: %.3f" % (n.sensorX, n.sensorY, n.sensorHeading, n.sensorAltitude, n.sensorDepth))
		# print("Complete reading s7k file :-)")
		reader.close()

	update_progress("Process Complete: ", (fileCounter/len(matches)))
	# if args.trackline:
	# 	if len(TLshp.records) > 0:
	# 		print ("Saving track line shapefile: %s" % trackLineFileName)
	# 		TLshp.save(trackLineFileName)
	# 		# now write out a prj file so the data has a spatial Reference
	# 		prj = open(trackLineFileName.replace('.shp','.prj'), 'w')
	# 		prj.write('GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]') # python will convert \n to os.linesep
	# 		prj.close() # you can omit in most cases as the destructor will call it
	# 	else:
	# 		print ("Nothing to save to SHP, file skipping")
###############################################################################
# def createTrackLine(reader, trackLine, step):
# 	lastTimeStamp = 0
# 	line_parts = []
# 	line = []
# 	navigation = reader.loadNavigation()

# 	if len(navigation) == 0:
# 		return

# 	# create the trackline shape file
# 	for update in navigation:
# 		if update.timestamp - lastTimeStamp >= step:
# 			line.append([float(update.sensorX),float(update.sensorY)])
# 			lastTimeStamp = update.timestamp
# 	# now add the very last update
# 	line.append([float(navigation[-1].sensorX),float(navigation[-1].sensorY)])

# 	line_parts.append(line)
# 	trackLine.line(parts=line_parts)
# 	# now add to the shape file.
# 	recDate = from_timestamp(navigation[0].timestamp).strftime("%Y%m%d")
# 	# write out the shape file FIELDS data
# 	trackLine.record(os.path.basename(reader.fileName), recDate)



# ###############################################################################
# def createSHP(fileName, geometrytype=shapefile.POLYLINE):
# 	'''open for append or create the shape files. This can be a polyline <false> or polygon '''
# 	if os.path.isfile(fileName):
# 		try:
# 			# Create a shapefile reader
# 			r = shapefile.Reader(fileName)
# 			# Create a shapefile writer
# 			# using the same shape type
# 			# as our reader
# 			writer = shapefile.Writer(r.shapeType)
# 			# Copy over the existing dbf fields
# 			writer.fields = list(r.fields)
# 			# Copy over the existing polygons
# 			writer._shapes.extend(r.shapes())
# 			# Copy over the existing dbf records
# 			writer.records.extend(r.records())
# 		except shapefile.error:
# 			print ("Problem opening existing shape file, aborting!")
# 			exit()
# 	else:
# 		writer = shapefile.Writer(geometrytype)
# 		writer.autoBalance = 1
# 	return writer

###############################################################################
# TIME HELPER FUNCTIONS
###############################################################################
def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()

def from_7ktimestamp(year, day, hour, minute, seconds):
	secs, millisecs = modf(seconds)
	# we need to remove a day!
	return datetime(year, 1, 1,0,0,0) + timedelta(days=day - 1 , hours=hour, minutes=minute, seconds=secs, milliseconds=millisecs*1000 )
	# datetime(days=day)

def from_timestamp(unixtime):
	return datetime.utcfromtimestamp(unixtime)

def dateToKongsbergDate(dateObject):
	return dateObject.strftime('%Y%m%d')

def dateToKongsbergTime(dateObject):
	return dateObject.strftime('%H%M%S')

def dateToSecondsSinceMidnight(dateObject):
	return (dateObject - dateObject.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

###############################################################################
def update_progress(job_title, progress):
	length = 20 # modify this to change the length
	block = int(round(length*progress))
	msg = "\r{0}: [{1}] {2}%".format(job_title, "#"*block + "-"*(length-block), round(progress*100, 2))
	if progress >= 1: msg += " DONE\r\n"
	sys.stdout.write(msg)
	sys.stdout.flush()

###############################################################################
###############################################################################
class s7kreader:
	'''class to read a Reson .s7k file'''
	header_def = '=2H4L2Hf2B H2L2HL 2H3L'
	header_len = struct.calcsize(header_def)
	header_unpack = struct.Struct(header_def).unpack_from

	recordTime = 0
	recordCounter = 0

	def __init__(self, s7kfileName):
		if not os.path.isfile(s7kfileName):
			print ("file not found:", s7kfileName)
		self.fileName = s7kfileName
		self.fileptr = open(s7kfileName, 'rb')
		self.fileSize = self.fileptr.seek(0, 2)
		# go back to start of file
		self.fileptr.seek(0, 0)
		# self.s7kFileHdr = s7kFILEHDR(self.fileptr)

	def __str__(self):
		return pprint.pformat(vars(self))

	def close(self):
		self.fileptr.close()

	def rewind(self):
		# go back to start of file
		self.fileptr.seek(0, 0)
		# self.s7kFileHdr = s7kFILEHDR(self.fileptr)

	def moreData(self):
		bytesRemaining = self.fileSize - self.fileptr.tell()
		# print ("current file ptr position:", self.fileptr.tell())
		bytesRemaining = max(bytesRemaining,0)

		return bytesRemaining

	###############################################################################
	def readDatagramHeader(self):
		'''read the common header for any datagram'''
		try:
			curr = self.fileptr.tell()
			data = self.fileptr.read(self.header_len)
			s = self.header_unpack(data)

			protocol				= s[0]
			offset					= s[1]
			syncpattern				= s[2]
			size					= s[3]
			optionaldataoffset		= s[4]
			optionaldataidentifier 	= s[5]
			year					= s[6]
			day						= s[7]
			seconds					= s[8]
			hour					= s[9]
			minute					= s[10]
			recordversion			= s[11]
			recordtypeidentifier 	= s[12]
			deviceidentifier		= s[13]
			reserved				= s[14]
			systemenumerator		= s[15]
			reserved				= s[16]
			flags					= s[17]
			reserved1				= s[18]
			reserved2				= s[19]
			totalrecordsinfragment	= s[20]
			fragmentnumber			= s[21]
			# datasection		
			# checksum
			self.date = from_7ktimestamp(year, day, hour, minute, seconds)
			numberofbytes 		= size
			typeofdatagram		= recordtypeidentifier

			version = recordversion
			# systemid = 1
			# echosounderid
			# time_sec
			# time_nanosec
			# self.date
			# now reset file pointer to the start of the datagram
			self.fileptr.seek(curr, 0)

			# we need to add 4 bytes as the message does not contain the 4 bytes used to hold the size of the message
			# trap corrupt datagrams at the end of a file.  We see this in EM2040 systems.
			# if (curr + numberofbytes + 4 ) > self.fileSize:
			# 	numberofbytes = self.fileSize - curr - 4
			# 	typeofdatagram = 'XXX'
			# 	return numberofbytes + 4, STX, typeofdatagram, EMModel, RecordDate, RecordTime

			return (numberofbytes, typeofdatagram, version, self.date)
			# return numberofbytes, typeofdatagram, version, systemid, echosounderid, time_sec, time_nanosec, self.date
		except struct.error:
			return 0,0,0,0,0,0,0,0


	###############################################################################
	def readDatagram(self):
		'''read the datagram header.  This permits us to skip datagrams we do not support'''
		numberofbytes, typeofdatagram, version, date = self.readDatagramHeader()
		self.recordCounter += 1
		self.recordTime = to_timestamp(date)
		if numberofbytes == 0:
			return "CORRUPT", None
	
		# if typeofdatagram == '#IIP': # Installation (Start)
		# 	dg = IIP_INSTALLATION(self.fileptr, numberofbytes)
		# 	return dg.typeofdatagram, dg
		# if typeofdatagram == '#IOP': # RUNTIME
		# 	dg = IOP_RUNTIME(self.fileptr, numberofbytes)
		# 	return dg.typeofdatagram, dg
		# if typeofdatagram == '#SVP': # Sound Velocity
		# 	dg = SVP(self.fileptr, numberofbytes)
		# 	return dg.typeofdatagram, dg
		# if typeofdatagram == '#SCL': # Clock
		# 	dg = CLOCK(self.fileptr, numberofbytes)
		# 	return dg.typeofdatagram, dg
		# if typeofdatagram == '#SKM': # ATTITUDE
		# 	dg = ATTITUDE(self.fileptr, numberofbytes)
		# 	return dg.typeofdatagram, dg
		if typeofdatagram == 1015: # Position
			dg = POSITION(self.fileptr, numberofbytes)
			return dg.typeofdatagram, dg
		# if typeofdatagram == '#MRZ': # Position
		# 	dg = RANGEDEPTH(self.fileptr, numberofbytes)
		# 	return dg.typeofdatagram, dg
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

				if (typeofdatagram == 1015):
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

	def computeSpeedFromPositions(self, navData):
		if (navData[0].sensorX <= 180) & (navData[0].sensorY <= 90): #data is in geographicals
			for r in range(len(navData) - 1):
				rng, bearing12, bearing21 = geodetic.calculateRangeBearingFromGeographicals(navData[r].sensorX, navData[r].sensorY, navData[r+1].sensorX, navData[r+1].sensorY)
				# now we have the range, comput the speed in metres/second. where speed = distance/time
				navData[r].sensorSpeed = rng / (navData[r+1].dateTime.timestamp() - navData[r].dateTime.timestamp())
		else:
			for r in range(len(navData) - 1):
				rng, bearing12, bearing21 = geodetic.calculateRangeBearingFromGridPosition(navData[r].sensorX, navData[r].sensorY, navData[r+1].sensorX, navData[r+1].sensorY)
				# now we have the range, comput the speed in metres/second. where speed = distance/time
				navData[r].sensorSpeed = rng / (navData[r+1].dateTime.timestamp() - navData[r].dateTime.timestamp())

		# now smooth the sensorSpeed
		speeds = [o.sensorSpeed for o in navData]
		npspeeds=np.array(speeds)

		smoothSpeed = geodetic.medfilt(npspeeds, 5)
		meanSpeed = float(np.mean(smoothSpeed))

		for r in range(len(navData) - 1):
			navData[r].sensorSpeed = float (smoothSpeed[r])

		return meanSpeed, navData

	# def readPacketheader(self):
	# 	data = self.fileptr.read(self.s7kPacketHeader_len)
	# 	s = self.s7kPacketHeader_unpack(data)

	# 	MagicNumber					= s[0]
	# 	HeaderType					 = s[1]
	# 	SubChannelNumber			   = s[2]
	# 	NumChansToFollow			   = s[3]
	# 	Reserved1					  = s[4]
	# 	Reserved2					  = s[5]
	# 	NumBytesThisRecord			 = s[6]

	# 	return HeaderType, SubChannelNumber, NumChansToFollow, NumBytesThisRecord

	# def readPacket(self):
	# 	ping = None
	# 	# remember the start position, so we can easily comput the position of the next packet
	# 	currentPacketPosition = self.fileptr.tell()

	# 	# read the packet header.  This permits us to skip packets we do not support
	# 	HeaderType, SubChannelNumber, NumChansToFollow, NumBytesThisRecord = self.readPacketheader()
	# 	if HeaderType == 0:
	# 		ping = s7kPINGHEADER(self.fileptr, self.s7kFileHdr, SubChannelNumber, NumChansToFollow, NumBytesThisRecord)

	# 		# now read the padbytes at the end of the packet
	# 		padBytes = currentPacketPosition + NumBytesThisRecord - self.fileptr.tell()
	# 		if padBytes > 0:
	# 			data = self.fileptr.read(padBytes)
	# 	else:
	# 		print ("unsupported packet type: %s at byte offset %s" % (HeaderType, currentPacketPosition))
	# 		self.fileptr.seek(currentPacketPosition + NumBytesThisRecord, 0)

	# 	return ping

	# def readChannel(self):
	#	 return s7kPINGCHANHEADER()

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
class POSITION:
	def __init__(self, fileptr, numberofbytes):
		self.typeofdatagram = 1015	# assign the code for this datagram type
		self.offset = fileptr.tell()	# remember where this packet resides in the file so we can return if needed
		self.numberofbytes = numberofbytes	# remember how many bytes this packet contains
		self.fileptr = fileptr		  # remember the file pointer so we do not need to pass from the host process
		self.fileptr.seek(numberofbytes, 1)	 # move the file pointer to the end of the record so we can skip as the default actions
		self.data = ""

	###############################################################################
	def read(self):
		self.fileptr.seek(self.offset, 0)# move the file pointer to the start of the record so we can read from disc

		rec_fmt = '=2H4L2Hf2B H2L2HL 2H3L' + "B2d6f"
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		s = rec_unpack(self.fileptr.read(rec_len))

		year							= s[6]
		day								= s[7]
		seconds							= s[8]
		hour							= s[9]
		minute							= s[10]
		self.date = from_7ktimestamp(year, day, hour, minute, seconds)

		self.verticalreference 			= s[22]
		self.latitude 					= math.degrees(s[23])
		self.longitude 					= math.degrees(s[24])
		self.horizontalpositionaccuracy	= s[25]
		self.vesselheight				= s[26]
		self.heightaccuracy				= s[27]
		self.speedoverground			= s[28]
		self.courseoverground			= math.degrees(s[29])
		self.heading					= math.degrees(s[30])

		# reset the file pointer to the end of the packet.
		self.fileptr.seek(self.offset + self.numberofbytes, 0)

###############################################################################
###############################################################################
if __name__ == "__main__":
	main()

