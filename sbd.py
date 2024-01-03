#name:			sbd_survey
#created:		May 2023
#by:			paul.kennedy@guardiangeomatics.com
#description:	python module to read an EIVA binary SBD file
#See readme.md for details

import os
import sys
import pprint
import struct
import time
from datetime import datetime, timezone


# local imports
from pathlib import Path
import sys
# path_root = Path(__file__).parents[2]
path_root = Path(__file__).parent
sys.path.append(str(path_root))

# import r2sonicdecode
# import refraction

# from sbd_survey import r2sonicdecode
# from sbd_survey import refraction

###############################################################################
def main():

	# filename = "C:/ggtools/sbd_survey/J355N001.SBD"
	# filename = "C:/sampledata/sbd_srov/231120002308.SBD"
	# filename = "c:/sampledata/sbd/Langenuen_SBD_North_v1/01_sbd/J354N003.SBD"
	filename = "C:/sampledata/sbd/badposition/J354N018.SBD"
	# filename =  "C:/sampledata/sbd_srov/231120002308.SBD"
	process(filename)	
		
###############################################################################
def process (filename):
	#open the SBD file for reading by creating a new SBDFReader class and passin in the filename to open.  The reader will read the initial header so we can get to grips with the file contents with ease.
	
	# print ( "Processing file:", filename)
	reader = SBDReader(filename)
	reader.SBDfilehdr.printsensorconfiguration()

	start_time = time.time() # time  the process

	while reader.moreData():
		category, decoded = reader.readdatagram()
		if category == reader.GYRO:
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))

		if category == reader.MOTION: # 3
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Motion: %s %.3f %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['roll'], sensor['pitch'], sensor['heave']))
		
		if category == reader.BATHY:  # 4
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Depth: %s %.3f" % (from_timestamp(msgtimestamp), sensor['depth']))

		if category == reader.POSITION: # 8
			sensorid, msgtimestamp, sensor, rawdata = decoded
			print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))

		if category == reader.ECHOSOUNDER: # 9
			sensorid, msgtimestamp, sensor, rawdata = decoded
			# print("Echosounder: %s %s " % (sensor['mbesname'], from_timestamp(msgtimestamp)))
			# if rawdata[0:4] == b'BTH0':
				#this is how we decode the BTH0 datagram from r2sonic 
				# BTHDatagram = r2sonicdecode.BTH0(rawdata)
				# depth_velocity_profile = [(0, 1500), (100, 1500), (200, 1500)]  # Example profile

				# for all the beams in the decoded datagram compute the depth
				# for idx, angle in enumerate(BTHDatagram.angles):
					# depth, acrosstrack = refraction.ray_trace_to_time(BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth_velocity_profile)
					# print("Beam %d Angle %.3f Range %.3f Depth %.3f acrosstrack %.3f " % (idx, BTHDatagram.angles[idx], BTHDatagram.ranges[idx], depth, acrosstrack))
					# using the  sensor gyro, easting, northing compute the positon on the sealfoor
					# print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))
					# print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))

	navigation, navigation2 = reader.loadnavigation()
	for n in navigation:
		print ("Date %s X: %.10f Y: %.10f Hdg: %.3f" % (from_timestamp(n[0]), n[1], n[2], n[3]))

	reader.close()
	print("Complete reading SBD file :-)")
	print ("Duration %.3fs" % (time.time() - start_time)) # print the processing time.

####################################################################################################################
####################################################################################################################
class SENSOR:
	def __init__(self, id=0, porttype=0, name="", sensorcategory=0, sensortype=0, ipaddress="0.0.0.0", port=0, offsetx = 0, offsety = 0, offsetz = 0, offsetheading = 0, offsetroll = 0, offsetpitch = 0, offsetheave = 0):

		self.id 			= id
		self.name 			= name
		self.sensorcategory	= sensorcategory
		self.sensortype 	= sensortype
		self.ipaddress		= ipaddress
		self.porttype 		= porttype
		self.port 			= port
		self.offsetx 		= offsetx
		self.offsety 		= offsety
		self.offsetz 		= offsetz
		self.offsetheading 	= offsetheading
		self.offsetroll 	= offsetroll
		self.offsetpitch 	= offsetpitch
		self.offsetheave 	= offsetheave

	#print the contents of the class
	def __str__(self):
		return (pprint.pformat(vars(self)))	
	
###############################################################################
class SBDFILEHDR:
	def __init__(self, fileptr):

		self.sensors = []

		#header is 60 bytes...
		SBDFileHdr_fmt = '<30h'
		# SBDFileHdr_fmt = '<2H 2L 24h'
		SBDFileHdr_len = struct.calcsize(SBDFileHdr_fmt)
		SBDFileHdr_unpack = struct.Struct(SBDFileHdr_fmt).unpack_from

		data = fileptr.read(SBDFileHdr_len)
		s = SBDFileHdr_unpack(data)
		# turn the unpack below

		self.header = {
			'sensorcount'		: s[7],
			'datastartbyte'		: s[8],
			'year'				: s[10],
			'month'				: s[11],
			'day'				: s[13],
			'hour'				: s[14],
			'minute'			: s[15],
			'second'			: s[16],
			'millisecond'		: s[17],
			'version'			: s[19],
		}
		self.date = datetime (self.header['year'], self.header['month'], self.header['day'], self.header['hour'], self.header['minute'], self.header['second'], self.header['millisecond'])

		# print("File Name %s " % (fileptr.name))
		# print("File Version %s " % (self.header['version']))
		# print("File Start Date %s " % (self.date))

		#geodesy is at offset 366 (80 bytes)
		fileptr.seek(366, 0)
		msg_fmt = '80s'
		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from
		data = fileptr.read(msg_len)
		s = msg_unpack(data)
		self.ellipsiod = s[0].decode('utf-8').rstrip('\x00')
		# print (self.ellipsiod)

		#geodesy UTM is at 446
		fileptr.seek(446, 0)
		msg_fmt = '80s'
		msg_len = struct.calcsize(msg_fmt)
		msg_unpack = struct.Struct(msg_fmt).unpack_from
		data = fileptr.read(msg_len)
		s = msg_unpack(data)
		self.projection = s[0].decode('utf-8').rstrip('\x00')
		# print (self.projection)
		
		#each sensor definition takes 256 bytes.  
		#looks like the sensor definition starts at byte 1060 with an ID and then a type (hex 0x424)
		#looks like sensor name is 32 bytes and the remaining 224 are not yet known

		# count		type,	un,	cat,	disabl,	un,un,un,un,name
		# 0 	0	(3,  	0, 	0,  	0, 		0, 0, 0, 0, b'NMEA ZDA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 1)
		# 1 	1	(26, 	0, 	2,  	0, 		0, 0, 0, 0, b'Sprint EM3000\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 2)
		# x  	2	(10, 	0, 	3,  	1, 		0, 0, 0, 0, b'Sprint EM3000RPH\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 2)
		# 2 	3	(16, 	0,	4,  	0, 		0, 0, 0, 0, b'SprintINGGA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 2)
		# 3 	4	(13, 	0, 	4,  	0, 		0, 0, 0, 0, b'Mini IPS\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 4)
		# 4 	5	(35, 	0, 	4,  	0, 		0, 0, 0, 0, b'VaisalaBaromet\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 4)
		# 5 	6	(6,  	0, 	5,  	0, 		0, 0, 0, 0, b'MiniSVS\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 4)
		# 6 	7	(6,  	0, 	8,  	0, 		0, 0, 0, 0, b'SprintINGGA\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 2)
		# 7 	8	(9,  	0, 	8,  	0, 		0, 0, 0, 0, b'ROV USBL\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 2)
		# x  	9	(9,  	0, 	8,  	1, 		0, 0, 0, 0, b'Stbd wheel\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 2)
		# x 	10	(33, 	0, 	9,  	1, 		0, 0, 0, 0, b'H1_R2Sonic 2000 series Dual \x00\x00\x00\x00', 2)
		# x 	11	(33, 	0, 	9,  	1, 		0, 0, 0, 0, b'H2_R2Sonic 2000 series Dual\x00\x00\x00\x00\x00', 2)
		# x 	12	(7,  	0, 	11, 	1, 		106, 5, 0, 0, b'OrionCableTracker\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 4)
		# x 	13	(2,  	0, 	11, 	1, 		0, 0, 0, 0, b'TSS 340/440/440mm\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00', 0)

		# print("Header Instrument record at byte offset: %d " % (fileptr.tell()))
		fileptr.seek(1060, 0)
		try:
			for idx in range(0,self.header['sensorcount'] + 1):
				msg_fmt 		= '8B 32s H'
				msg_len 		= struct.calcsize(msg_fmt)
				msg_unpack 		= struct.Struct(msg_fmt).unpack_from
				data 			= fileptr.read(msg_len)
				hdr 				= msg_unpack(data)
				sensortype		= hdr[0] # as per instruments.xml file in naviscan folder
				unknown1		= hdr[1]
				sensorcategory	= hdr[2]
				sensordisabled	= hdr[3]	
				unknown3		= hdr[4]	
				unknown4		= hdr[5]	
				unknown5		= hdr[6]	
				unknown6		= hdr[7]	
				sensorname 		= hdr[8].decode('utf-8').rstrip('\x00')
				porttype		= hdr[9]
				# print("sensorname %s disabled %d" % (sensorname, sensordisabled))

				#now we need to read the rest of the structure based on the port type		
				if porttype == 1: # serial ports...
					#looks like we need 14 bytes for a com port definition
					msg_fmt 		= '<7H 11f 78H'
					msg_len 		= struct.calcsize(msg_fmt)
					msg_unpack 		= struct.Struct(msg_fmt).unpack_from
					data 			= fileptr.read(msg_len)
					s 				= msg_unpack(data)
					# sensordisabled 		= s[0]
					port 			= s[1]
					baud 			= s[3]
					parity 			= s[4]
					databits 		= s[5]
					stopbits 		= s[6]
					ipaddress = str("0.0.0.0")
					latency			= s[8]
					offsetx			= s[10]
					offsety			= s[11]
					offsetz			= s[12]
					depthc_o	= s[13]
					offsetroll		= s[14]
					offsetpitch		= s[15]
					offsetheading	= s[16]
					# offsetheave		= s[16]
					gravity			= s[18]

				elif porttype == 2: # UDP ports...
					msg_fmt 		= '<2H 6B 11f 80H'
					#looks like we need 14 bytes for a ethernet port definition
					msg_len 		= struct.calcsize(msg_fmt)
					msg_unpack 		= struct.Struct(msg_fmt).unpack_from
					data 			= fileptr.read(msg_len)
					s 				= msg_unpack(data)
					portnumber 		= s[1]
					ip1 			= s[4]
					ip2 			= s[5]
					ip3 			= s[6]
					ip4 			= s[7]
					ipaddress = str("%d.%d.%d.%d" % (ip1, ip2, ip3, ip4))
					stopbits 		= s[7]
					latency			= s[9]
					offsetx			= s[10]
					offsety			= s[11]
					offsetz			= s[12]
					# offsetheading	= s[13]
					offsetroll		= s[14]
					offsetpitch		= s[15]
					offsetheading	= s[16]
					# offsetheave		= s[16]
					gravity			= s[18]
					depthc_o	= s[13]

				elif porttype == 4: # ATTU ports...
					msg_fmt 		= '<2H 6B 11f 80H'
					#looks like we need 14 bytes for a ethernet port definition
					msg_len 		= struct.calcsize(msg_fmt)
					msg_unpack 		= struct.Struct(msg_fmt).unpack_from
					data 			= fileptr.read(msg_len)
					s 				= msg_unpack(data)
					portnumber 		= s[1]
					ip1 			= s[4]
					ip2 			= s[5]
					ip3 			= s[6]
					ip4 			= s[7]
					ipaddress = str("%d.%d.%d.%d" % (ip1, ip2, ip3, ip4))
					stopbits 		= s[7]
					latency			= s[9]
					offsetx			= s[10]
					offsety			= s[11]
					offsetz			= s[12]
					# offsetheading	= s[13]
					offsetroll		= s[14]
					offsetpitch		= s[15]
					# offsetheave		= s[16]
					offsetheading	= s[16]
					gravity			= s[18]
					depthc_o	= s[13]

				else: # anything else
					msg_fmt 		= '<2H 6B 11f 80H'
					#looks like we need 14 bytes for a ethernet port definition
					msg_len 		= struct.calcsize(msg_fmt)
					msg_unpack 		= struct.Struct(msg_fmt).unpack_from
					data 			= fileptr.read(msg_len)
					s 				= msg_unpack(data)
					portnumber 		= s[1]
					ip1 			= s[4]
					ip2 			= s[5]
					ip3 			= s[6]
					ip4 			= s[7]
					ipaddress = str("%d.%d.%d.%d" % (ip1, ip2, ip3, ip4))
					stopbits 		= s[7]
					latency			= s[9]
					offsetx			= s[10]
					offsety			= s[11]
					offsetz			= s[12]
					# offsetheading	= s[13]
					offsetroll		= s[14]
					offsetpitch		= s[15]
					# offsetheave		= s[16]
					offsetheading	= s[16]
					gravity			= s[18]
					depthc_o	= s[13]

				#skip the disabled sensors
				if sensordisabled != 0:
					continue

				sensor = SENSOR(idx, porttype, sensorname, sensorcategory, sensortype, ipaddress, port, offsetx, offsety, offsetz, offsetheading, offsetroll, offsetpitch, offsetheave)
				# print (idx, sensor.name)

				self.sensors.append(sensor)
		except:
			print("oops, reading header sensor problem.  will continue (this is not a problem)")

		# thats the header complete. we can now advance to the datagrams...
		#the header has a pointer to the start of the data, so lets set the file pointer there now.		
		fileptr.seek(self.header['datastartbyte']+20,0)
		# print("Completed reading header at byte offset: %d " % (fileptr.tell()))

	#########################################################################################
	def printsensorconfiguration(self):
		#print the sensor definitions
		for sensor in self.sensors:
			print (sensor)

	#########################################################################################
	def __str__(self):
		return (pprint.pformat(vars(self)))

#########################################################################################
class SBDReader:
	'''now lets try to read the data packet header which is 32 bytes...'''
	# hdr_fmt = '=16h' # we know this works....
	# hdr_fmt = '<4h 2L 2H'
	# hdr_fmt = '<2L 2L L'
	# hdr_fmt = '<4H 2L L'
	# hdr_fmt = '<2L 2L L'
	hdr_fmt = '<L 4B 2L L'
	hdr_len = struct.calcsize(hdr_fmt)
	hdr_unpack = struct.Struct(hdr_fmt).unpack_from

	#SENSOR CATEGORY
	GNSSTIME 			= 0
	RUNLINECONTROL 		= 1
	GYRO 				= 2
	MOTION				= 3
	BATHY		 		= 4
	AUXILIARY		 	= 5
	RAWDATA		 		= 6
	DOPPLER		 		= 7
	POSITION 			= 8
	ECHOSOUNDER			= 9
	SIDESCAN			= 10 #0x00a
	PIPETRACKER			= 11 #0x00b
	#thats all of the categories from the insutruments.xml file in naviscan

	#########################################################################################
	def __init__(self, SBDfilename):
		if not os.path.exists(SBDfilename):
			print ("file not found:", SBDfilename)
		self.filename = SBDfilename
		self.fileptr = open(SBDfilename, 'rb')
		self.filesize = self.fileptr.seek(0, 2)
		# go back to start of file
		self.fileptr.seek(0, 0)

		if self.filesize < 30:
			# do not open impossibly small files.
			self.fileptr.close()
			return
		#the file is of a sensible size so open it.
		self.SBDfilehdr = SBDFILEHDR(self.fileptr)

		self.sensor = {}
		self.sensor['timestamp'] = 0
		self.sensor['gyro'] = 0
		self.sensor['gyromc'] = 0
		self.sensor['roll'] = 0
		self.sensor['pitch'] = 0
		self.sensor['heave'] = 0
		self.sensor['depth'] = 0
		self.sensor['velocity'] = 0
		self.sensor['easting'] = 0
		self.sensor['northing'] = 0
		self.sensor['mbesname'] = ""

	#########################################################################################
	def readdatagram(self):
		'''now lets try to read the data packet header which is 32 bytes...'''

		# remember the start position, so we can easily comput the position of the next packet
		currentPacketPosition = self.fileptr.tell()
		# print("reading datagram from currentpos %d %s" % (currentPacketPosition, hex(currentPacketPosition)))

		data = self.fileptr.read(self.hdr_len)
		msghdr = self.hdr_unpack(data)

		# when assuming header is using bytes...
		sensorid 					= msghdr[0]
		unknown1 					= msghdr[1]
		unknown2 					= msghdr[2]
		unknown3 					= msghdr[3]
		unknown3 					= msghdr[4]
		msgunixtimeseconds 			= msghdr[5]
		msgunixtimemicroseconds 	= msghdr[6]
		msgtimestamp 				= msgunixtimeseconds + (msgunixtimemicroseconds / 1000000)
		msglen 						= msghdr[7] #we know this works...!!!!

		if msglen == 0:
			return None, [None, None, None, None]
		try:
			category = sensorid % 256
			# if more than 256 is the secondary system we need to deal with this correctly but dont have enough informat at present so assume they are all primary
		except:
			category = 0
			print("OOPS sensorid not found, skipping bytes %d" % (msglen))
			self.fileptr.read(msglen)
			return None, [None, None, None, None]

		if category == self.GYRO: # 2
			msg_fmt 	= '< 3f 2H' + str(msglen-16) + 's' 
			msg_fmt 	= '< 3f L' + str(msglen-16) + 's' 
			msg_len 	= struct.calcsize(msg_fmt)
			msg_unpack 	= struct.Struct(msg_fmt).unpack_from
			data 		= self.fileptr.read(msg_len)
			s1 			= msg_unpack(data)
			gyro 		= s1[0]
			gyromc 		= s1[2] 
			rawdata 	= s1[4]
			self.sensor['timestamp'] = msgtimestamp
			self.sensor['gyro'] = gyro
			self.sensor['gyromc'] = gyromc
			return category, [sensorid, msgtimestamp, self.sensor, rawdata]
		
		elif category == self.MOTION: # 3
			msg_fmt 	= '< 3f 2H' + str(msglen-16) + 's' 
			msg_fmt 	= '< 3f L' + str(msglen-16) + 's' 
			msg_len 	= struct.calcsize(msg_fmt)
			msg_unpack 	= struct.Struct(msg_fmt).unpack_from
			data 		= self.fileptr.read(msg_len)
			s1 			= msg_unpack(data)
			roll 		= s1[0] # verified
			pitch 		= s1[1] # verified
			heave 		= s1[2] # verified
			packetsize 	= s1[3]
			rawdata 	= s1[4]
			self.sensor['timestamp'] = msgtimestamp
			self.sensor['roll'] = roll
			self.sensor['pitch'] = pitch
			self.sensor['heave'] = heave
			return category, [sensorid, msgtimestamp, self.sensor, rawdata]
		
		elif category == self.BATHY: # 4
			msg_fmt 	= '< 3f L' + str(msglen-16) + 's'
			msg_len 	= struct.calcsize(msg_fmt)
			msg_unpack 	= struct.Struct(msg_fmt).unpack_from
			data 		= self.fileptr.read(msg_len)
			s1 			= msg_unpack(data)
			depth 		= s1[0]
			unknown 	= s1[1]
			unknown 	= s1[2]
			# packetsize 	= s1[3]
			rawdata 	= s1[4]
			self.sensor['timestamp'] = msgtimestamp
			self.sensor['depth'] = depth
			return category, [sensorid, msgtimestamp, self.sensor, rawdata]
		
		elif category == self.AUXILIARY: # 5
			msg_fmt 	= '< f' + str(msglen-4) + 's'
			msg_len 	= struct.calcsize(msg_fmt)
			msg_unpack 	= struct.Struct(msg_fmt).unpack_from
			data 		= self.fileptr.read(msg_len)
			s1 			= msg_unpack(data)
			velocity 	= s1[0]
			# unknown 	= s1[1]
			# unknown 	= s1[2]
			# packetsize= s1[3]
			rawdata 	= s1[1]
			self.sensor['timestamp'] = msgtimestamp
			self.sensor['velocity'] = velocity
			return category, [sensorid, msgtimestamp, self.sensor, rawdata]
		
		elif category == self.POSITION: # 8
			msg_fmt = '< 2d L' + str(msglen-20) + 's' # easting, northing, packetsize, 0, data pkpk the 3rd word could be a long int??
			# for the first 20 bytes, 16-20 are unsigned shorts.  16-18 are the msg size, 19-20 are 0
			msg_len 	= struct.calcsize(msg_fmt)
			msg_unpack 	= struct.Struct(msg_fmt).unpack_from
			data 		= self.fileptr.read(msg_len)
			s1 			= msg_unpack(data)
			easting 	= s1[0]
			northing 	= s1[1]
			packetsize 	= s1[2]
			rawdata 	= s1[3]
			self.sensor['timestamp'] = msgtimestamp
			self.sensor['easting'] = easting
			self.sensor['northing'] = northing
			return category, [sensorid, msgtimestamp, self.sensor, rawdata]

		elif category == self.ECHOSOUNDER: # 9
			#for a MBES there is no decoded section.  its just the raw bytes, starting with BTH0 for a reson 2024 or MRZ
			msg_fmt 	= '< ' + str(msglen) + 's' 
			msg_len 	= struct.calcsize(msg_fmt)
			msg_unpack 	= struct.Struct(msg_fmt).unpack_from
			data 		= self.fileptr.read(msg_len)
			s1 			= msg_unpack(data)
			rawdata 	= s1[0]
			self.sensor['timestamp'] = msgtimestamp
			self.sensor['mbesname'] = rawdata[0:4]
			#check to see if the rawdata first 4 bytes are BTH0
			# if rawdata[0:4] == b'BTH0':
			# 	#this is how we decode the BTH0 datagram
			# 	BTHDatagram = r2sonicdecode.BTH0(rawdata)
			return category, [sensorid, msgtimestamp, self.sensor, rawdata]
		
		else:
			print("OOPS sensorid %d not found, skipping bytes %d" % (sensorid, msglen))
			data = self.fileptr.read(msglen)
			return None, [None, None, None, None]

	#########################################################################################
	def __str__(self):
		return pprint.pformat(vars(self))

	#########################################################################################
	def close(self):
		self.fileptr.close()

	#########################################################################################
	def rewind(self):
		# go back to start of file
		self.fileptr.seek(0, 0)
		self.SBDfilehdr = SBDFILEHDR(self.fileptr)

	#########################################################################################
	def moreData(self):
		bytesRemaining = self.filesize - self.fileptr.tell()
		# print ("current file ptr position:", self.fileptr.tell())
		return bytesRemaining

	#########################################################################################
	def getfirstcoordinate(self):
		'''we sometimes need to guess the EPSG and for that we need the first coordinate in the file so read it and quit'''
		self.rewind()
		while self.moreData() > 0:
			category, decoded = self.readdatagram()

			if category == self.POSITION: # 8
				sensorid, msgtimestamp, sensor, rawdata = decoded
				self.rewind()
				return (msgtimestamp, sensor['easting'], sensor['northing'], sensor['gyro'])
		return 0,0,0,0

	#########################################################################################
	def loadnavigation(self, step=1):
		
		navigation = []
		navigation2 = []
		previoustimestamp = 0
		self.rewind()
		start_time = time.time() # time the process
		while self.moreData() > 0:
			category, decoded = self.readdatagram()

			if category == self.GYRO:
				sensorid, msgtimestamp, sensor, rawdata = decoded
				# print("Gyro: %s %.3f" % (from_timestamp(msgtimestamp), sensor['gyro']))

			if category == self.POSITION: # 8
				sensorid, msgtimestamp, sensor, rawdata = decoded
				if msgtimestamp  - previoustimestamp >= step:
					navigation.append([msgtimestamp, sensor['easting'], sensor['northing'], sensor['gyro']])
					navigation2.append(sensor)
					previoustimestamp = msgtimestamp

				# print("Position: %s %.3f %.3f" % (from_timestamp(msgtimestamp), sensor['easting'], sensor['northing']))
				# nmeastring=rawdata.decode('utf-8').rstrip('\x00')
				# nmeaobject = NMEAReader.parse(nmeastring,VALCKSUM=0)
				# navigation.append([msgtimestamp, nmeaobject.lon, nmeaobject.lat, heading])

		self.rewind()
		# print("Get navigation Range Duration %.3fs" % (time.time() - start_time)) # print the processing time.
		return (navigation, navigation2)

###############################################################################
# TIME HELPER FUNCTIONS
###############################################################################
def to_timestamp(dateObject):
	return (dateObject - datetime(1970, 1, 1)).total_seconds()

def from_timestamp(unixtime):
	# return datetime.utcfromtimestamp(unixtime)
	return datetime.fromtimestamp(unixtime, tz=timezone.utc)

#########################################################################################
#########################################################################################
if __name__ == "__main__":
	main()
