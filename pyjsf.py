#name:		  	pyjsf
#created:		November 2021
#by:			paul.kennedy@guardiangeomatics.com
#description:   python module to read EDGETECHY JSF file format
#notes:		 	See main at end of script for example how to use this

# See readme.md for more details

import ctypes
import math
import pprint
import struct
import os.path
import time
from datetime import datetime
from datetime import timedelta

def main():
	#open the ALL file for reading by creating a new s7kReader class and passin in the filename to open.
	filename =   "C:/projects/survey2ssdmtest/SBP-0039-PA7-20200214-172048.JSF"

	r = jsfreader(filename)
	pingCount = 0
	start_time = time.time() # time the process

	navigation = r.loadNavigation()
	#print("Load Navigation Duration: %.2fs" % (time.time() - start_time)) # time the process
	# print (navigation)

	while r.moreData():
		# read a datagram.  If we support it, return the datagram type and aclass for that datagram
		# The user then needs to call the read() method for the class to undertake a fileread and binary decode.  This keeps the read super quick.
		typeOfDatagram, datagram = r.readdatagram()
		print(typeOfDatagram, end=',')

		rawbytes = r.readDatagramBytes(datagram.offset, datagram.numberOfBytes)
		# hereis how we compute the checksum
		# print(sum(rawbytes[5:-3]))

		if typeOfDatagram == '80':
			datagram.read()
			# print (datagram.data, datagram.latitude, datagram.longitude)
			r.fileptr.seek(datagram.offset + datagram.numberOfBytes, 0)# move the file pointer to the start of the record so we can read from disc
			continue

	print("Read Duration: %.3f seconds, pingCount %d" % (time.time() - start_time, pingCount)) # print the processing time. It is handy to keep an eye on processing performance.

	r.rewind()
	print("Complete reading ALL file :-)")
	r.close()

class jsfreader:
	'''class to read a RESON 7k file'''
	packetheader_fmt = '=HBBHBBBBHL'
	packetheader_len = struct.calcsize(packetheader_fmt)
	packetheader_unpack = struct.Struct(packetheader_fmt).unpack_from

	def __init__(self, filename=None):
		if filename is not None:
			if not os.path.isfile(filename):
				print ("file not found:", filename)
			self.fileName = filename
			self.fileptr = open(filename, 'rb')
			self.fileSize = os.path.getsize(filename)
			self.recordDate = ""
			self.recordTime = ""
			self.recordCounter=0

	def __str__(self):
		return pprint.pformat(vars(self))

	def currentRecordDateTime(self):
		'''return a python date object from the current datagram objects raw date and time fields '''
		if self.recordDate == 0:
			return datetime.now()
		date_object = datetime.strptime(str(self.recordDate), '%Y%m%d') + timedelta(0,self.recordTime)
		return date_object

	def to_DateTime(self, recordDate, recordTime):
		'''return a python date object from a split date and time record'''
		date_object = datetime.strptime(str(recordDate), '%Y%m%d') + timedelta(0,recordTime)
		return date_object

	# def to_timestamp(self, dateObject):
	#	 '''return a unix timestamp from a python date object'''
	#	 return (dateObject - datetime(1970, 1, 1)).total_seconds()


	def close(self):
		'''close the current file'''
		self.fileptr.close()

	def rewind(self):
		'''go back to start of file'''
		self.fileptr.seek(0, 0)

	def currentPtr(self):
		'''report where we are in the file reading process'''
		return self.fileptr.tell()

	def moreData(self):
		'''report how many more bytes there are to read from the file'''
		return self.fileSize - self.fileptr.tell()

	def readdatagramheader(self):
		'''read the common header for any datagram'''
		try:
			curr = self.fileptr.tell()
			data = self.fileptr.read(self.packetheader_len)
			s = self.packetheader_unpack(data)

			syncmarker				= s[0]
			protocolversion 		= s[1]
			sessionidentifier		= s[2]
			recordtypeidentifier	= s[3]
			commandtype				= s[4]
			subsystemnumber			= s[5]
			channel					= s[6]
			sequencenumber			= s[7]
			reserved				= s[8]
			sizeoffollowingmessage	=s[9]
			numberOfBytes	= self.packetheader_len + sizeoffollowingmessage

			# year		  	= s[6]
			# day	  			= s[7]
			# seconds 		= s[8]
			# hours			= s[9]
			# minutes			= s[10]
			# reserved 		= s[11]
			# self.recorddate = datetime(year=year, month=1, day=1)
			# self.recorddate += timedelta(
			# 	# subtract 1 since datetime already starts at 1
			# 	days=day - 1,
			# 	hours=hours,
			# 	minutes=minutes,
			# 	seconds=seconds,
			# )			
			# now reset file pointer
			self.fileptr.seek(curr, 0)
			
			self.recorddate = None
			return numberOfBytes, recordtypeidentifier, self.recorddate
		except struct.error:
			return 0,0,0,0,0,0

	def readDatagramBytes(self, offset, byteCount):
		'''read the entire raw bytes for the datagram without changing the file pointer.  this is used for file conditioning'''
		curr = self.fileptr.tell()
		self.fileptr.seek(offset, 0)# move the file pointer to the start of the record so we can read from disc
		data = self.fileptr.read(byteCount)
		self.fileptr.seek(curr, 0)
		return data

	def getRecordCount(self):
		'''read through the entire file as fast as possible to get a count of all records.  useful for progress bars so user can see what is happening'''
		count = 0
		start = 0
		end = 0
		self.rewind()
		numberOfBytes, readdatagramheader, recorddate = self.readdatagramheader()
		start = recorddate # to_timestamp(to_DateTime(RecordDate, RecordTime))
		self.rewind()
		while self.moreData():
			numberOfBytes, STX, typeOfDatagram, EMModel, RecordDate, RecordTime = self.readdatagramheader()
			self.fileptr.seek(numberOfBytes, 1)
			count += 1
		self.rewind()
		end = to_timestamp(to_DateTime(RecordDate, RecordTime))
		return count, start, end

	def readdatagram(self):
		'''read the datagram header.  This permits us to skip datagrams we do not support'''
		numberOfBytes, recordtypeidentifier, recorddate = self.readdatagramheader()
		self.recordCounter += 1

		if recordtypeidentifier == 80: 
			dg = P_80(self.fileptr, numberOfBytes, recorddate)
			return dg.recordtypeidentifier, dg
		else:
			dg = UNKNOWN_RECORD(self.fileptr, numberOfBytes, recordtypeidentifier)
			return dg.recordtypeidentifier, dg
			# self.fileptr.seek(numberOfBytes, 1)
###############################################################################
	def loadInstallationRecords(self):
		'''loads all the installation into lists'''
		installStart 	= None
		installStop 	= None
		# initialMode 	= None
		datagram 		= None
		self.rewind()
		while self.moreData():
			typeOfDatagram, datagram = self.readdatagram()
			if (typeOfDatagram == 'I'):
				installStart = self.readDatagramBytes(datagram.offset, datagram.numberOfBytes)
				datagram.read()
			if (typeOfDatagram == 'i'):
				installStop = self.readDatagramBytes(datagram.offset, datagram.numberOfBytes)
				break
		self.rewind()
		return installStart, installStop

###############################################################################
	def loadCenterFrequency(self):
		'''determine the central frequency of the first record in the file'''
		centerFrequency = 0
		self.rewind()
		while self.moreData():
			typeOfDatagram, datagram = self.readdatagram()
			if (typeOfDatagram == 'N'):
				datagram.read()
				centerFrequency = datagram.CentreFrequency[0]
				break
		self.rewind()
		return centerFrequency
###############################################################################
	def loadDepthMode(self):
		'''determine the central frequency of the first record in the file'''
		initialDepthMode = ""
		self.rewind()
		while self.moreData():
			typeOfDatagram, datagram = self.readdatagram()
			if typeOfDatagram == 'R':
				datagram.read()
				initialDepthMode = datagram.DepthMode
				break
		self.rewind()
		return initialDepthMode
###############################################################################
	def loadNavigation(self, firstRecordOnly=False):
		'''loads all the navigation into lists'''
		navigation 					= []
		selectedPositioningSystem 	= None
		self.rewind()
		while self.moreData():
			typeOfDatagram, datagram = self.readdatagram()
			if typeOfDatagram == '80':
				datagram.read()
				#print (datagram.data, datagram.latitude, datagram.longitude)
				self.fileptr.seek(datagram.offset + datagram.numberOfBytes, 0)# move the file pointer to the start of the record so we can read from disc
				#trap impossible values
				if (datagram.longitude != 0) and (datagram.latitude != 0):
					navigation.append([to_timestamp(datagram.recorddate), datagram.longitude, datagram.latitude])
				else:
					print("skipping zero latitude, longitudes")
		self.rewind()
		return navigation


###############################################################################
class P_80:
	def __init__(self, fileptr, numberOfBytes, recorddate):
		self.recordtypeidentifier = '80'	# assign the code for this datagram type
		self.offset = fileptr.tell()	# remember where this packet resides in the file so we can return if needed
		self.numberOfBytes = numberOfBytes			  # remember how many bytes this packet contains
		self.fileptr = fileptr		  # remember the file pointer so we do not need to pass from the host process
		self.fileptr.seek(numberOfBytes, 1)	 # move the file pointer to the end of the record so we can skip as the default actions
		self.data = ""
		self.recorddate = recorddate

	def read(self):
		self.fileptr.seek(self.offset, 0)# move the file pointer to the start of the record so we can read from disc
		hdr = jsfreader().packetheader_fmt
		rec_fmt = hdr + 'lLLHH HHH6sh HHhh h2hf32sllh'
		rec_len = struct.calcsize(rec_fmt)
		rec_unpack = struct.Struct(rec_fmt).unpack
		# bytesRead = rec_len
		s = rec_unpack(self.fileptr.read(rec_len))
		
		self.unixtime 					= s[10]
		self.startdepth	  				= s[11]
		self.pingnumber					= s[12]
		self.reserved1		 			= s[13]
		self.reserved2 					= s[14]
		self.msb						= s[15]
		self.lsb						= s[16]
		self.lsb2						= s[17]
		self.reserved3					= s[18]
		self.idcode						= s[19]
		self.validityflag				= s[20]
		self.reserved4					= s[21]
		self.dataformat					= s[22]
		self.laybackalongtrackdistance	= s[23]
		self.laybackacrosstrackdistance	= s[24]
		self.reserved5					= s[25]
		self.kilometrespipe				= s[26]
		self.reserved6					= s[27] 
		self.reserved7					= s[28] 
		self.longitude					= (s[29] / 10000) / 60
		self.latitude					= (s[30] / 10000) / 60
		self.units						= s[31]

		self.recorddate = from_timestamp(self.unixtime)

		return

###############################################################################
class UNKNOWN_RECORD:
	'''used as a convenience tool for datagrams we have no bespoke classes.  Better to make a bespoke class'''
	def __init__(self, fileptr, numberOfBytes, recordtypeidentifier):
		self.recordtypeidentifier = recordtypeidentifier
		self.offset = fileptr.tell()
		self.numberOfBytes = numberOfBytes
		self.fileptr = fileptr
		self.fileptr.seek(numberOfBytes, 1)
		self.data = ""
	def read(self):
		self.data = self.fileptr.read(self.numberOfBytes)


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
