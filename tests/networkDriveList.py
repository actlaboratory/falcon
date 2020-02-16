import win32wnet
import socket

h=win32wnet.WNetOpenEnum(5,1,0,None)
	#5=RESOURCE_CONTEXT
	#1=RESOURCETYPE_DISK
lst=win32wnet.WNetEnumResource(h,64)	#65以上の指定不可
win32wnet.WNetCloseEnum(h);
lst.pop(0)

for l in lst:
	print("------------------")
	print(l.lpLocalName)
	print(l.lpRemoteName)
	for address in socket.getaddrinfo(l.lpRemoteName[2:],None):
		print(address[4][0])

#動かない時は下記を参考にサービスを起動するとよい
#https://itojisan.xyz/trouble/12595/#3