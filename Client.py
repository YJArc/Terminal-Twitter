import os
import sys
import signal
import socket
from threading import Thread
import time
import pickle
import getpass
from collections import namedtuple
 
TAB = "     "

#=======================================================================
# Signal Hander - in case client goes rogue we tell server to stop caring
#=======================================================================

def signal_handler(signal, frame):
	s.send("KILL")
	l.close()
	s.close()

	print TAB,'You\'ve gone rogue huh?'
	sys.exit(0)
    
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)
signal.signal(signal.SIGTSTP, signal_handler)


#=======================================================================
# Structures for implementation
#=======================================================================

# Note: messages once set are immutable (cannot be edited)
Message = namedtuple("Message", "msg hashtags")
Message2 = namedtuple("Message", "user msg hashtags")
current_user = ""


#=======================================================================
# Globals for establishing connection
#=======================================================================

TCP_IP = ''
TCP_PORT = 3505
BUFF_SIZE = 1024


#=======================================================================
# Start Connection (TCP)
#======================================================================= 

#Service connection
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(60)
s.connect((TCP_IP, TCP_PORT))

#listen connection
l = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#l.settimeout(60)
l.connect((TCP_IP, TCP_PORT))


#=======================================================================
# Twitter implementation
#=======================================================================

#-----LIVE FEED---------------------------------------------------------
def live_msgs():
	while True:
		msg = pickle.loads (l.recv(BUFF_SIZE))
		print "User: ", msg[0] #user
		print "Message: ", msg[1] #msg
		print "Hashtags: ", msg[2] #hashtags
		


#-----LOGIN-------------------------------------------------------------
def login():
	global current_user
	print "Please enter your credentials"
	while True:
		user = raw_input("User: ")
		s.send(user)
		password = getpass.getpass("Password: ")
		s.send(password)
		response = s.recv(BUFF_SIZE)
		print response
		if (response == "Login Successful!"):
			current_user = user
			menu_selector()

#-----MENU OPTIONS------------------------------------------------------		
#-----General User Options----------------------------------------------
def offline_msg():
	#notify server what we are going to do
	s.send("offline_msgs")
	pkt = s.recv(BUFF_SIZE)
	msgs_pkt = pickle.loads(pkt)
	for msg in msgs_pkt:
		#~ message = Message2 (src_pkt[i][0],src_pkt[i][1],src_pkt[i][2])
		print "User: ", msg[0] #user
		print "Message: ", msg[1] #msg
		print "Hashtags: ", msg[2] #hashtags
	return

def edit_subs():
	#notify server what we are going to do
	s.send("edit_subs")
	print "Enter \"Q!\" to return to Menu at any time"
	while True:
		print TAB, "(1) Delete Subscription"
		print TAB, "(2) Add Subscription"
		sel = raw_input(">>     ")
		if (sel == "Q!"):
			s.send("Q!")
			return
		elif (sel == "1"):
			s.send("del_sub")
			subs = pickle.loads(s.recv(BUFF_SIZE))
			print subs
			while True:
				del_sub = raw_input("Enter the username of the subscription to remove: ")
				if (del_sub == "Q!"):
					s.send("Q!")
					return
				s.send(del_sub)
				response = s.recv(BUFF_SIZE)
				if (response == "valid_user"):
					print "User has been removed from your subscriptions."
					return
				elif (response == "invalid_user"):
					print "The user does not exist in your subscription!"
					continue
			
		elif (sel == "2"):
			s.send("add_sub")
			while True:
				add_sub = raw_input("Enter the username of the new subscription: ")
				if (add_sub == "Q!"):
					s.send("Q!")
					return
				s.send(add_sub)
				response = s.recv(BUFF_SIZE)
				if (response == "valid_user"):
					print "User has been added to your subscriptions!"
					return
				elif (response == "invalid_user"):
					print "The user does not exist or you are already subscribed to the user!"
					continue
		else:
			print "Selection not supported. Please select 1-4"
			
	return

def post_msg():
	#Because we handle UI in client only notify server
	#when we will ACTUALLY send something since user can quit prematurely
	# "post_msg" sent after message fully built
	
	#prompt user to enter message
	print "Enter \"Q!\" to return to Menu at any time"
	while True:
		msg = raw_input("Enter your message: ")
		if (msg == "Q!"):
			return
		if (len(msg) > 140):
			print "Messages must be 140 characters or less"
			continue
		if (len(msg) == 0):
			print "Messages cannot be empty"
			continue
		else:
			break
	#prompt user to add tags seperately
	hashtags = []
	print "Enter \"q!\" to stop adding hashtags"
	while True:
		tag = raw_input("Enter hashtags: ")
		if(tag == "Q!"):
			return
		if (tag == "q!"):
			break
		else:
			hashtags.append(tag)
	#notify the server what we are going to do
	s.send("post_msg")
	#package the message
	message = Message (msg, hashtags)
	msg_pkt = pickle.dumps(message)
	s.send(msg_pkt)
	
	return
	
def hash_search():
	print "Enter \"Q!\" to return to Menu at any time"
	query = raw_input("Enter your hashtag search query: ")
	if (query == "Q!"):
		return
	else:
		s.send("hash_search")
		s.send(query)
		result_size = s.recv(BUFF_SIZE)
		pkt = s.recv(BUFF_SIZE)
		srch_pkt = pickle.loads(pkt)
		for i in xrange(0,int(result_size)):
			#~ message = Message2 (src_pkt[i][0],src_pkt[i][1],src_pkt[i][2])
			print srch_pkt[i][0]
			print srch_pkt[i][1]
			print srch_pkt[i][2]
	
	return
			
def logout():
	global current_user
	current_user = ""
	#notify server what we are going to do
	s.send("logout")
	return

#-----Admin Only Option-------------------------------------------------
def msg_count():
	s.send("msg_count")
	msg_count = s.recv(BUFF_SIZE)
	print "The Server is handling [ ", msg_count, " ] messages"
	return
	

def user_count():
	s.send("user_count")
	user_count = s.recv(BUFF_SIZE)
	print "The Server is handling [ ", user_count, " ] users"
	return

# implementation is optional
def stored_count():
	s.send("user_count")
	user_count = s.recv(BUFF_SIZE)
	print "The Server is handling [ ", user_count, " ] unread messages"
	return
# implementation is optional
def new_user():
	
	return


#-----MENU SELECTOR-----------------------------------------------------
def menu_selector():
	global current_user
	print "Welcome, ", current_user
	offline_count = s.recv(BUFF_SIZE)
	print "you have [ ", offline_count , " ] unread messages"
	
	while True:
		print "Main Menu:"
		print TAB, "(1) See Offline Messages"
		print TAB, "(2) Edit Subscriptions"
		print TAB, "(3) Post a Message"
		print TAB, "(4) Search a hashtag"
		print TAB, "(5) Logout"
		selection = raw_input(">>     ")
			
		if (selection == "1"):
			offline_msg()
		elif (selection == "2"):
			edit_subs()
		elif (selection == "3"):
			post_msg()
		elif (selection == "4"):
			hash_search()
		elif (selection == "5"):
			logout()
			login()
		elif (selection == "messagecount" and current_user == "admin"):
			msg_count()		
		elif (selection == "usercount"and current_user == "admin"):
			user_count()	
		elif (selection == "storedcount"and current_user == "admin"):
			stored_count()
		elif (selection == "newuser"and current_user == "admin"):
			new_user() 		#not implemented yet
		else:
			print "Selection not supported. Please select 1-4"
	return
#=======================================================================
# BEGIN
#=======================================================================

thread = Thread(target = live_msgs, args = ()) #thread captures live feed
thread.setDaemon(True) #kill thread when main dies
thread.start()
login()
s.close()
l.close()
