##------------------------------------------
##--- Original script from :
##--- Author: Pradeep Singh
##--- Blog: https://iotbytes.wordpress.com/record-audio-from-phone-line-with-raspberry-pi
##--- Date: 25th June 2018
##--- Version: 1.0
##--- Python Ver: 3.7
##--- Modified by fr3d
##--- Description:
##--- 1 pick a list of  incommings calls
##--- 2 record the audio msg.
##--- 3 translate to text
##--- 4 test to database
##--- 5 database to sms
##--- 6 database to web
##--- and the
##--- Hardware: Raspberry Pi3 and SIM 800 HAT
##------------------------------------------


import serial
import time
import threading
import atexit
import sys
import re
import wave
from datetime import datetime
import os
import fcntl
import subprocess



RINGS_BEFORE_AUTO_ANSWER = 2 #Must be greater than 1
MODEM_RESPONSE_READ_TIMEOUT = 30  #Time in Seconds (Default 120 Seconds)
#MODEM_NAME = 'U.S. Robotics'    # Modem Manufacturer, For Ex: 'U.S. Robotics' if the 'lsusb' cmd output is similar to "Bus 001 Device 004: ID 0baf:0303 U.S. Robotics"
MODEM_NAME = 'SIM800L'    # Modem Manufacturer,



# Record Voice Variables
REC_VM_MAX_DURATION = 20  # Time in Seconds
#REC_VM_MAX_DURATION = 120  # Time in Seconds

# Used in global event listener
disable_modem_event_listener = True

# Global Modem Object
analog_modem = serial.Serial()

audio_file_name = ''

#=================================================================
# Set COM Port settings
#=================================================================
def set_COM_port_settings(com_port):
	analog_modem.port = com_port
	#analog_modem.port = '/dev/ttyS0'
	analog_modem.baudrate = 115200 #57600 #9600 #115200
	analog_modem.bytesize = serial.EIGHTBITS #number of bits per bytes
	analog_modem.parity = serial.PARITY_NONE #set parity check: no parity
	analog_modem.stopbits = serial.STOPBITS_ONE #number of stop bits
	analog_modem.timeout = 3         #non-block read
	analog_modem.xonxoff = False     #disable software flow control
	analog_modem.rtscts = False      #disable hardware (RTS/CTS) flow control
	analog_modem.dsrdtr = False      #disable hardware (DSR/DTR) flow control
	analog_modem.writeTimeout = 3    #timeout for write
#=================================================================



#=================================================================
# Initialize Modem
#=================================================================
def detect_COM_port():
#+fred not working ptyhon3
	# List all the Serial COM Ports on Raspberry Pi
	#proc = subprocess.Popen(['ls /dev/tty[A-Za-z]*'], shell=True, stdout=subprocess.PIPE)
	proc = subprocess.Popen(['ls /dev/tty[A-Za-z]*'], shell=True, stdout=subprocess.PIPE)
	com_ports = str(proc.communicate()[0])
	com_ports_list = com_ports.split('\n')

	# Find the right port associated with the Voice Modem
	for com_port in com_ports_list:
		if 'ttyS0' in com_port:
		#if 'serial' in com_port:
			#Try to open the COM Port and execute AT Command
			try:
				# Set the COM Port Settings
				set_COM_port_settings(com_port)
				analog_modem.open()
			except:
				print ("DETECT: Unable to open COM Port: " + com_port)
				pass
			else:
				#Try to put Modem in Voice Mode
				#if not exec_AT_cmd("AT+FCLASS=8", "OK"):
				if not exec_AT_cmd("AT", "OK"):
					print ("DETECT: Error: Failed to get AT.")
					#if analog_modem.isOpen():
					#analog_modem.close()
					serial.close()
				else:
					# Found the COM Port exit the loop
					print ("DETECT: Modem COM Port is: " + com_port)
					analog_modem.flushInput()
					analog_modem.flushOutput()
					break
#=================================================================



#=================================================================
# Initialize Modem
#=================================================================
def init_modem_settings():

	# Detect and Open the Modem Serial COM Port
	try:
		detect_COM_port()
	except:
		print ("INIT Error: Unable to open the Serial Port.")
		sys.exit()

	# Initialize the Modem
	try:
		# Flush any existing input outout data from the buffers
		analog_modem.flushInput()
		analog_modem.flushOutput()

		# Test Modem connection, using basic AT command.
		if not exec_AT_cmd("AT"):
			print ("INIT Error: Unable to access the Modem AT")
		else:
			print ("INIT success: access to the Modem AT")

		# reset to factory default.
		if not exec_AT_cmd("ATZ"):
			print ("INIT Error: Unable reset to factory default")
		else:
			print ("INIT success: reset to factory default ATZ")

		# set pin.
		if not exec_AT_cmd("AT+CPIN=8743"):
			print ("INIT Error: Unable to set PiN")
		else:
			print ("INIT success: set PiN")


		# Display result codes in verbose form
		if not exec_AT_cmd("AT+CMEE=2"):
			print ("INIT Error: Unable set verbose form")
		else:
			print ("INIT success: set verbose form AT+CMEE=2")

		# Enable Command Echo Mode.
		if not exec_AT_cmd("ATE1"):
			print ("INIT Error: Failed to enable Command Echo Mode")
		else:
			print ("INIT success: enable Command Echo Mode ATE1")

		# Display product name.
		if not exec_AT_cmd("ATI"):
			print ("INIT Error: Display product name and product release information.")
		else:
			print ("INIT success: enable Display ATI")

		# Display phone number.
		if not exec_AT_cmd("At+clip=1"):
			print ("INIT Error: Display phone number.")
		else:
			print ("INIT success: enable Display phone number.")

		# Display Connected Line Identification Presentation.
		if not exec_AT_cmd("At+colp=1"):
			print ("INIT Error: Connected Line Identification Presentation.")
		else:
			print ("INIT success: Connected Line Identification Presentation.")

		# Enable date and time.
		if not exec_AT_cmd("AT+CLTS=1;&W"):
			print ("INIT Error: Enable date and time.")
		else:
			print ("INIT success: Enable date and time.")

		# deregistering from network to update time.
		if not exec_AT_cmd("AT+COPS=2"):
			print ("INIT Error: deregistering from network.")
		else:
			print ("INIT success: deregistering from network.")

		# reregistering from network to update time.
		if not exec_AT_cmd("AT+COPS=0"):
			print ("INIT Error: reregistering from network.")
		else:
			print ("INIT success: reregistering from network.")


		# Flush/cleaning any existing input outout data from the buffers
		analog_modem.flushInput()
		analog_modem.flushOutput()

	except:
		print ("INIT Error: unable to Initialize the Modem")
		sys.exit()
#=================================================================



#=================================================================
# Reset Modem
#=================================================================
def reset_USB_Device():

	# Close the COM Port if it's open
	try:
		if analog_modem.isOpen():
			analog_modem.close()
	except:
		pass
	"""
	# Equivalent of the _IO('U', 20) constant in the linux kernel.
	USBDEVFS_RESET = ord('U') << (4*2) | 20
	dev_path = ""

	# Bases on 'lsusb' command, get the usb device path in the following format -
	# /dev/bus/usb/<busnum>/<devnum>
	proc = subprocess.Popen(['lsusb'], stdout=subprocess.PIPE)
	out = proc.communicate()[0]
	lines = out.split('\n')
	for line in lines:
		if MODEM_NAME in line:
			parts = line.split()
			bus = parts[1]
			dev = parts[3][:3]
			dev_path = '/dev/bus/usb/%s/%s' % (bus, dev)

	# Reset the USB Device
	fd = os.open(dev_path, os.O_WRONLY)
	try:
		fcntl.ioctl(fd, USBDEVFS_RESET, 0)
		print ("Modem reset successful"
	finally:
		os.close(fd)
	"""
	# Re-initialize the Modem
	init_modem_settings()
#=================================================================



#=================================================================
# Execute AT Commands at the Modem
#=================================================================
def exec_AT_cmd(modem_AT_cmd, expected_response="OK"):

	global disable_modem_event_listener
	disable_modem_event_listener = True

	try:
		# Send command to the Modem
		analog_modem.write((modem_AT_cmd + "\r").encode())
		# Read Modem response
		execution_status = read_AT_cmd_response(expected_response)
		disable_modem_event_listener = False
		# Return command execution status
		return execution_status

	except:
		disable_modem_event_listener = False
		print ("Error: Failed to execute the command")
		print ("modem_AT_cmd : ", modem_AT_cmd)
		return False
#=================================================================



#=================================================================
# Read AT Command Response from the Modem
#=================================================================
def read_AT_cmd_response(expected_response="OK"):

	# Set the auto timeout interval
	start_time = datetime.now()

	try:
		while 1:
			# Read Modem Data on Serial Rx Pin
			modem_response = analog_modem.readline()
			print (modem_response)
			# Recieved expected Response
			if expected_response == modem_response.strip(' \t\n\r' + chr(16)):
				return True
			# Failed to execute the command successfully
			elif "ERROR" in modem_response.strip(' \t\n\r' + chr(16)):
				return False
			# Timeout
			elif (datetime.now()-start_time).seconds > MODEM_RESPONSE_READ_TIMEOUT:
				return False

	except:
		print ("Error in read_modem_response function...")
		return False
#=================================================================



#=================================================================
# Recover Serial Port
#=================================================================
def recover_from_error():
	# Stop Global Modem Event listener
	global disable_modem_event_listener
	disable_modem_event_listener = True

	# Reset USB Device
	#no need gsm hat
	reset_USB_Device()

	# Start Global Modem Event listener
	disable_modem_event_listener = False
#=================================================================



#=================================================================
# Read DTMF Digits
#=================================================================
def dtmf_digits(modem_data):
	digits = ""
	digit_list = re.findall('/(.+?)~', modem_data)
	for d in digit_list:
		digits= digits + d[0]
	return digits
#=================================================================


#=================================================================
# Terminate the call
#=================================================================
def kill_call():
		time.sleep(25)
#		exec_AT_cmd("ATH","OK")
		if not exec_AT_cmd("ATH"):
			print ("KILL_CALL: Error: - Failed to terminate the call")
			print ("Trying to recover serial port")
			recover_from_error()
		else:
			print ("KILL_CALL: Elapsed time: Call Terminated")
#=================================================================


#=================================================================
# Play DTMF
#=================================================================
def play_dtmf():
# DTMF code.
	if not exec_AT_cmd('AT+CLDTMF=5,"5,3,6,8",45',"OK"):
		print ("RECORD: Error: Failed to play DTMF code.")
		#return
	else:
		print ("RECORD: Success: Played DTMF code.")
		record_audio()

#=================================================================


#=================================================================
# Call Server
#=================================================================
def call_server():
# DTMF code.
	if not exec_AT_cmd("atd+33328590545I;","OK"):
	#if not exec_AT_cmd("atd+33800943376I;","OK"):
		print ("CALLSERVER: Error: Failed making call.")
		#return
	else:
		print ("CALLSERVER: Success: calling...")
		#waitinng for boring message
		time.sleep(5)
		play_dtmf()
		# now connected kill call in 25sec
		kill_call()

#=================================================================


#=================================================================
# Record wav file (Voice Msg/Mail)
#=================================================================
def record_audio():
	print ("Record Audio Msg - Start")

	# Enter Voice Mode
	if not exec_AT_cmd("AT","OK"):
		print ("RECORD: Error: Handshake Failed.")
		return
	else:
		print ("RECORD: Success: Handshake")

	"""
		# Set speaker volume to normal
		if not exec_AT_cmd("AT+VGT=128","OK"):
			print ("RECORD: Error: Failed to set speaker volume to normal."
			return

		# Compression Method and Sampling Rate Specifications
		# Compression Method: 8-bit linear / Sampling Rate: 8000MHz
		if not exec_AT_cmd("AT+VSM=128,8000","OK"):
			print ("RECORD: Error: Failed to set compression method and sampling rate specifications."
			return

		# Disables silence detection (Value: 0)
		if not exec_AT_cmd("AT+VSD=128,0","OK"):
			print ("RECORD: Error: Failed to disable silence detection."
			return

		# Put modem into TAD Mode
		if not exec_AT_cmd("AT+VLS=1","OK"):
			print ("RECORD: Error: Unable put modem into TAD mode."
			return

		# Enable silence detection.
		# Select normal silence detection sensitivity
		# and a silence detection interval of 5 s.
		if not exec_AT_cmd("AT+VSD=128,50","OK"):
			print ("RECORD: Error: Failed tp enable silence detection."
			return

		# Play beep.
		if not exec_AT_cmd("AT+VTS=[933,900,100]","OK"):
			print ("RECORD: Error: Failed to play 1.2 second beep."
			#return

		# Select voice receive mode
		if not exec_AT_cmd("AT+VRX","CONNECT"):
			print ("RECORD: Error: Unable put modem into voice receive mode."
			return
	"""
	# Record Audio File

	global disable_modem_event_listener
	disable_modem_event_listener = True


	# Set the auto timeout interval
	start_time = datetime.now()
	CHUNK = 1024
	audio_frames = []

	while 1:
		# Read audio data from the Modem
		audio_data = analog_modem.read(CHUNK)

		# Check if <DLE>b is in the stream
		if ((chr(16)+chr(98)) in audio_data):
			print ("RECORD: Busy Tone... Call will be disconnected.")
			break

		# Check if <DLE>s is in the stream
		if ((chr(16)+chr(115)) in audio_data):
			print ("RECORD: Silence Detected... Call will be disconnected.")
			break

		# Check if <DLE><ETX> is in the stream
		if (("<DLE><ETX>").encode() in audio_data):
			print ("RECORD: <DLE><ETX> Char Recieved... Call will be disconnected.")
			break

		# Timeout
		elif ((datetime.now()-start_time).seconds) > REC_VM_MAX_DURATION:
			print ("Timeout - Max recording limit reached.")
			break

		# Add Audio Data to Audio Buffer
		audio_frames.append(audio_data)

	global audio_file_name

	# Save the Audio into a .wav file
	wf = wave.open(audio_file_name, 'wb')
	wf.setnchannels(1)
	wf.setsampwidth(1)
	wf.setframerate(8000)
	wf.writeframes(b''.join(audio_frames))
	wf.close()

	# Reset Audio File Name
	audio_file_name = ''


	# Send End of Voice Recieve state by passing "<DLE>!"
	if not exec_AT_cmd((chr(16)+chr(33)),"OK"):
		print ("RECORD: Error: Unable to signal end of voice receive state")

	# Hangup the Call
	if not exec_AT_cmd("ATH","OK"):
		print ("RECORD: Error: Unable to hang-up the call")

	# Enable global event listener
	disable_modem_event_listener = False

	print ("RECORD: Record Audio Msg - END")
	return

#=================================================================


#=================================================================
# Data Listener
#=================================================================
def read_data():

	global disable_modem_event_listener
	ring_data = ""

	while 1:

		if not disable_modem_event_listener:
			modem_data = analog_modem.readline()


			if modem_data != "":
				print (modem_data)

				# Check if <DLE>b is in the stream
				if (chr(16)+chr(98)) in modem_data:
					#Terminate the call
					if not exec_AT_cmd("ATH"):
						print ("Error: Busy Tone - Failed to terminate the call")
						print ("Trying to recover the serial port")
						recover_from_error()
					else:
						print ("Busy Tone: Call Terminated")

				# Check if <DLE>s is in the stream
				if (chr(16)+chr(115)) == modem_data:
					#Terminate the call
					if not exec_AT_cmd("ATH"):
						print ("Error: Silence - Failed to terminate the call")
						print ("Trying to recover the serial port")
						recover_from_error()
					else:
						print ("Silence: Call Terminated")


				if ("-s".encode() in modem_data) or (("<DLE>-s").encode() in modem_data):
					print ("silence found during recording")
					analog_modem.write(("<DLE>-!" + "\r").encode())




				if ("RING" in modem_data) or ("DATE" in modem_data) or ("TIME" in modem_data) or ("NMBR" in modem_data):
					global audio_file_name
					if ("NMBR" in modem_data):
						from_phone = (modem_data[5:]).strip()
					if ("DATE" in modem_data):
						call_date =  (modem_data[5:]).strip()
					if ("TIME" in modem_data):
						call_time =  (modem_data[5:]).strip()
					if "RING" in modem_data.strip(chr(16)):
						ring_data = ring_data + modem_data
						ring_count = ring_data.count("RING")
						if ring_count == 1:
							pass
						elif ring_count == RINGS_BEFORE_AUTO_ANSWER:
							ring_data = ""
							audio_file_name = from_phone + "_" + call_date + "_" + call_time + "_" + str(datetime.strftime(datetime.now(),"%S")) + ".wav"
							from_phone = ''
							call_date = ''
							call_time = ''

							record_audio()

#=================================================================



#=================================================================
# Close the Serial Port
#=================================================================
def close_modem_port():

	# Try to close any active call
	try:
		exec_AT_cmd("ATH")
	except:
		pass

	# Close the Serial COM Port
	try:
		if analog_modem.isOpen():
			analog_modem.close()
			print ("Serial Port closed...")
	except:
		print ("Error: Unable to close the Serial Port.")
		sys.exit()
#=================================================================


# Main Function
init_modem_settings()

# Close the Modem Port when the program terminates
atexit.register(close_modem_port)

#call server & play dtmf
call_server()

#wait a few second

#play dtmf
#play_dtmf()

# Monitor Modem Serial Port
read_data()
