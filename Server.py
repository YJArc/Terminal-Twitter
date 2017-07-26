import sys
import socket
from threading import Thread
import time
import pickle
from collections import namedtuple

#=======================================================================
# Globals for establishing connection
#=======================================================================

HOST = ''        # My server's host
PORT = 3505      # My server's port

BUFF_SIZE = 1024


#=======================================================================
# Structures for implementation of Twitter
#=======================================================================

TAB = "     " #A variable that makes writing print a bit easier for me

Message = namedtuple("Message", "user msg hashtags")

class User:
	def __init__(self, username, password, followers, following, offline_msgs, online, listeners):
		self.username = username
		self.password = password
		self.followers = followers
		self.following = following
		self.offline_msgs = offline_msgs
		self.online = online
		self.listeners = listeners


#=======================================================================
# Database
#=======================================================================

client_list = []

#userbase = [ User(username, password, followers, following, offline_msgs, online, listeners), ...]
#           [     (str       str       list str   list str   list Message   bool   tcp conn), ...]
user_base = [ User("a", "a", [], [], [], False, []),
			  User("b", "b", [], [], [], False, []),
			  User("c", "c", [], [], [], False, []),
			  User("d", "d",[], [], [], False, []),
			  User("admin","password",[], [], [], False, []) ]

logged_count = 0;

msg_base = []


#=======================================================================
# Load and/or setup Database
#=======================================================================

def load_messages():	#implementation is optional

	return
	
def load_users(): 		#implementation is optional
	
	return

#=======================================================================
# Twitter implementation
#=======================================================================

#-----Client is dead protocol-------------------------------------------
# When a client dies it will send a "KILL" to server so it can be
# removed from the client_list and essentially logged out
def kill_client(client,client_listen, user):
	global logged_count
	#no longer serve the client
	for c in client_list:
		if c[0] == client:
			client_list.remove(c)
	#user might still be logged on in some other client
	#so we account for that
	if (len(user.listeners) <= 1):
		user.online = False
		logged_count -= 1
	#remove current client's listening thread since it broke connection
	user.listeners.remove(client_listen)
	#check user online status from server
	for u in user_base:
		print u.username, TAB, u.online
	sys.exit()

#-----Login-------------------------------------------------------------
#
def login(client,client_listen):
	global logged_count
	#loop until logged in then exit
	while True:
		#boolean to restart this while loop cleanly
		not_found = True
		
		#retrieve username
		username = client.recv(BUFF_SIZE)
		
		if (username == "KILL"): # ~~~ KILL check ~~~
			print "A user tried to login and exited. killing it's thread"
			sys.exit()
			
		print "User [ ", username , " ] trying to login"
		#retrieve password
		password = client.recv(BUFF_SIZE)
		
		if (password == "KILL"): # ~~~ KILL check ~~~
			print "A user tried to login and exited. killing it's thread"
			thread.exit()
			
		for user in user_base:					 #find our user
			if ((username,password) == (user.username, user.password)):
				print username, " logged in successfully."
				client.send("Login Successful!") #notify client on success
				if not (user.online):             #multi-client logins do not add to count
					logged_count += 1
				user.online = True                  #mark user as online
				user.listeners.append(client_listen) #multiple logged clients can listen to feed
				menu(client,client_listen, user)    #start taking requests
				not_found = False                   #break search and restart login at while loop
		
		if (not_found): #when we didn't find user in above for loop send a fail
			print "Sending fail."
			client.send("Login Failed.")             #notify client on fail
	
	#This section of this func shouldn't be reachable
	client.close()
	return

#-----MENU OPTIONS------------------------------------------------------
#-----General User Options----------------------------------------------

#offline messages: when a user is offline, messages posted by subs are
#pushed to offline_msgs
def offline_msg(client, user):
	#client.send(str(len(user.offline_msg))
	offline_msg_pkt = pickle.dumps(user.offline_msgs)
	client.send(offline_msg_pkt)
	del user.offline_msgs[:]
	return

#Edit subscriptions: add or remove a subscription. if name DNE in userbase
#ignore request. if name is self ignore request. Also updates sub's followers
def edit_subs(client, client_listen, user):
	
	sel = client.recv(BUFF_SIZE)
	
	if (sel == "KILL"): # ~~~ KILL check ~~~
		kill_client(client, client_listen, user)
	if (sel == "Q!"):   #quit function check
		return
		
	elif(sel == "del_sub"): #User wants to delete a subscription
		#send over their subscriptions so selection is easier
		client.send(pickle.dumps([u.username for u in user.following]))
		
		while True:
			#let them select a subscription
			sub = client.recv(BUFF_SIZE)
			
			if (sub == "KILL"): # ~~~ KILL check ~~~
				kill_client(client, client_listen, user)
			if (sub == "Q!"):   #quit function check
				return
			
			for u in user.following:
				if (u.username == sub):
					u.followers.remove(user) #sub no longer followed by user
					user.following.remove(u)        #user no longer following sub
					client.send("valid_user") #notify on valid selection
					return
			client.send("invalid_user") #user not found notify client
			continue
		
	elif(sel == "add_sub"): #User wants to add a subscription
		
		while True:
			#let user select a new subscription
			sub = client.recv(BUFF_SIZE)
			
			if (sub == "KILL"): # ~~~ KILL check ~~~
				kill_client(client, client_listen, user)
			if (sub == "Q!"):   #quit func check
				return
				
			if (sub == user.username):    #selction is user. Can't sub to self
				client.send ("invalid_user")
				continue
			elif (sub in [u.username for u in user.following]): #already sub'd to selection
				client.send("invalid_user")
				continue
			else:                         #selection DNE or already following
				for u in user_base:
					if (u.username == sub):
						u.followers.append(user)  #sub followed by user
						user.following.append(u)  #user following sub
						client.send("valid_user") #notify on valid selection
						return
				client.send("invalid_user")
				continue

	return
	
def post_msg(client, client_listen, user):
	#recieve the packet
	pkt = client.recv(BUFF_SIZE)
	if (pkt == "KILL"): # ~~~ KILL check ~~~
		kill_client(client, client_listen, user)
	
	msg_pkt = pickle.loads(pkt)
	message = Message(user.username, msg_pkt[0], msg_pkt[1])
	msg_base.append(message)
	
	print "Server will be posting the following to online accounts: "
	print message.user
	print message.msg
	print message.hashtags
	
	for u in user.followers:
		if (u.online):
			msg_pkt = pickle.dumps(message)
			for listener in u.listeners:  #send message to every client listening
				listener.send(msg_pkt)
		else:
			u.offline_msgs.append(message)
	return

def hash_search(client, client_listen, user):
	#hashtag we will search our message database for
	query = client.recv(BUFF_SIZE)
	
	if (selection == "KILL"): # ~~~ KILL check ~~~
		kill_client(client, client_listen, user)
	
	srch_results = []
	srch_len = 0
	for msg in reversed(msg_base):
		if (srch_len == 10):
			break
		for h in msg.hashtags:
			if (query == h):
				srch_results.append(msg)
				srch_len+=1
	client.send(str(srch_len))
	srch_pkt = pickle.dumps(srch_results)
	client.send(srch_pkt)

def logout(client_listen, user):
	global logged_count
	if (len(user.listeners) <= 1):
		user.online = False
		logged_count -= 1
	user.listeners.remove(client_listen)
	return
	
#-----Admin Only Option----------------------------------------------

def msg_count(client):
	client.send(str(len(msg_base)))
	return
	
def user_count(client):
	client.send(str(logged_count))
	return


def stored_count(client):
	count = 0
	for u in user_base:
		count += len(u.offline_msgs)
	client.send(str(count))
	return
# implementation is optional
def new_user(client):
	
	return

#-----MENU OPTION SELECTOR----------------------------------------------

def menu(client,client_listen, user):
	time.sleep(.05)
	#notify user on any offline messages
	client.send(str(len(user.offline_msgs)))
	#wait for user instruction
	while True:
		
		selection = client.recv(BUFF_SIZE)
		
		if (selection == "KILL"): # ~~~ KILL check ~~~
			kill_client(client, client_listen, user)
		if (selection == "offline_msgs"):
			offline_msg(client, user)
		elif (selection == "edit_subs"):
			edit_subs(client, client_listen, user)
		elif (selection == "post_msg"):
			post_msg(client, client_listen, user)
		elif (selection == "hash_search"):
			hash_search(client, client_listen, user)
		elif (selection == "logout"):
			logout(client_listen, user)
			return
		elif (selection == "msg_count" and user.username == "admin"):
			msg_count(client)
		elif (selection == "user_count"and user.username == "admin"):
			user_count(client)		#implementation is optional
		elif (selection == "stored_count"and user.username == "admin"):
			stored_count(client)	#implementation is optional
		elif (selection == "new_user"and user.username == "admin"):
			new_user(client) 		#implementation is optional
		else:
			continue


#=======================================================================	
# Start Connection (TCP)
#=======================================================================

try:
	#create an AF_INET, STREAM socket (TCP)
	serv_sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
except socket.error, msg:
	print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]
	sys.exit()
    
print 'Socket Created'

serv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

try:
    serv_sock.bind((HOST, PORT))
except socket.error, msg:
	print 'Bind failed. Error Code : ' + str(msg[0]) + ' , Error message : ' + msg[1]
	sys.exit()

print 'Socket Bind Complete'

serv_sock.listen(5)
print 'Socket now listening...'

# Accept connections and start serving some data
#=======================================================================
while True:
	#accept new connections
	client, addr = serv_sock.accept()
	client_list.append((client,addr))
	#accept a connection so the client listens to server
	client_listen, addr2 = serv_sock.accept()
	print "Now connected to " , addr
	#Create a thread for the connection
	thread = Thread(target = login, args = (client,client_listen))
	thread.start()
	print "We will now be serving this client"
	
