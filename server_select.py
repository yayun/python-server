#coding:utf-8

import select
import socket
import Queue
import sys

config=open("./config.txt","r")
list=config.readlines()
address=list[0].replace("\n","")
port=int(list[1].replace("\n",""))
config.close()
server=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server.setblocking(False)
server_address=(address,port)
server.bind(server_address)
server.listen(10)
inputs=[ server ]
#socket to whilch we except to write
outputs=[]
input_queues={}
while 1:

    print 'Waiting for the next event'
    #call select to block and wait for network activity
    readable, writable, exceptional = select.select(inputs, outputs, inputs)
  
    for s in readable:
        if s is server:
            #a "readable" server socket is ready to accept a connection
            connection, client_address = s.accept()
            print 'new connection from', client_address
            connection.setblocking(0)
            inputs.append(connection)
            input_queues[connection] = Queue.Queue()
        else:
            #an established connection with a client that has sent data.
            data = s.recv(1024)
            if data:
                print 'received "%s" from %s' % (data, s.getpeername())
                input_queues[s].put(data)
                if s not in outputs:
                    outputs.append(s)
            else:
                print 'closing', client_address, 'after reading no data'
                if s in outputs:
                    outputs.remove(s)
                inputs.remove(s)
                del input_queues[s]
    for s in writable:
        try:
            send_data="HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
            send_data+="hello world"
            open_file=open("./index.html","r").read()
            send_data+=open_file
            input_queues[s].put(send_data)
            next_msg = input_queues[s].get_nowait()
            s.send(next_msg)
            '''request=input_queues[s].get()
            header=request.split("\n")[1] 
            #file=header.split(" ")[1]
            send="HTTP/1.1 200 OK\r\nContent-Type: image/jpg\r\n\r\n"
            img=open("./like.jpg",'r').read()
            send+=img
            input_queues[s].put(send)
            msg=input_queues[s].get_nowait()
            s.send(msg)'''
            #Remove and return an item from the queue without blocking
        except Queue.Empty:
            print 'output queue for', s.getpeername(), 'is empty'
            outputs.remove(s)
        else:
            #print 'sending "%s" to %s' % (next_msg, s.getpeername())
            #s.send(next_msg)
            if s in outputs:
                outputs.remove(s)
            s.close()
            inputs.remove(s)
    for s in exceptional:
        print  'handling exceptional condition for', s.getpeername()
        inputs.remove(s)
        if s in outputs:
            outputs.remove(s)
        s.close()
        del input_queues[s]
