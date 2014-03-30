#coding:utf-8

import select
import socket


class HttpHandler(object):
    def __init__(self, conn, state='ready'):
        conn.setblocking(False)
        self.conn = conn
        self.fileno = conn.fileno()
        self.state = 'ready'
        self.input = ''
        self.output = ''
        self.n_sent_bytes = 0

    def get_path(self):
        lines = self.input.split("\n")
        for line in lines:
            if line.startswith('GET '):
                path = line.split(' ')[1]
                if path == '/':
                    path = '/index.html'
                if path.startswith('/'):
                    path = path[1:]
                return path
        return 'index.html'

    def get_mime_type(self):
        # http://reference.sitepoint.com/html/mime-types-full
        path = self.get_path()
        if '.' in path:
            suffix = path.split('.')[1]
            mime_types = {
                    "jpg": "image/jpeg",
                    "html": "text/html",
                    "txt": "text/plain",
                    "js": "text/javascript",
                    "css": "text/stylesheets"
            }
            return mime_types.get(suffix, 'text/html')
        return 'text/html'

    def process_output(self):
        path = self.get_path()
        mime_type = self.get_mime_type()
        try:
            with open(path, 'r') as f:
                data = f.read()
            header = "HTTP/1.1 200 OK\r\nContent-Type: %s\r\n\r\n%s\r\n"
            self.output = header % (mime_type, data)
            return self.output
        except IOError as e:
            self.output = "HTTP/1.1 404 Not Found\r\n\r\n404 Not Found"

    def read_step(self):
        data = self.conn.recv(1024)
        # print 'read_step %s: %s' % (self.fileno, [data])
        self.input += str(data)
        if len(data) < 1024 or not self.input:
            # print 'read_step %s: EOF: %s' % (self.fileno, self.input)
            self.state = 'read_done'
            self.process_output()
            return False
        self.state = 'reading'
        return True

    def write_step(self):
        if not self.state in ['read_done', 'writing']:
            return True
        data = self.output[self.n_sent_bytes:]
        # print 'write_step %s: %s' % (self.fileno, [data])
        try:
            self.state = 'writing'
            nbytes = self.conn.send(data)
            self.n_sent_bytes += nbytes
            if nbytes == 0 or self.n_sent_bytes >= len(self.output):
                return self.write_finish()
            return True
        except socket.error as e:
            print 'socket.error ----- %s' %e
            return self.write_finish()

    def write_finish(self):
        self.state = 'write_done'
        self.conn.close()
        return False

def map_fd_list(sockets):
    return [s.fileno() for s in sockets]

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.setblocking(False)
config = open("./config.txt", "r").readlines()
address = config[0].replace("\n", "")
port = int(config[1].replace("\n", ""))
server_address=(address,port)
server.bind(server_address)
server.listen(100)
inputs = set([server])
outputs = set([])
http_handlers = {}

while 1:
    print 'Waiting for the next event'
    # call select to block and wait for network activity
    # print {'inputs': map_fd_list(inputs), 'outputs': map_fd_list(outputs) }
    readables, writables, exceptionals = select.select(inputs, outputs, [])
    print {'readables': map_fd_list(readables), 'writables': map_fd_list(writables), 'exceptionals': map_fd_list(exceptionals)}

    for s in readables:
        if s is server:
            try:
                while True:
                    connection, address = s.accept()
                    print 'new connection: (%s) %s' % (connection.fileno(), connection.getpeername())
                    http_handlers[connection.fileno()] = HttpHandler(connection)
                    inputs.add(connection)
            except socket.error:
                pass

        else:
            handler = http_handlers[s.fileno()]
            handler.read_step()
            if handler.state == 'read_done':
                inputs.discard(s)
                outputs.add(s)

    for s in writables:
        if not http_handlers[s.fileno()].write_step():
            outputs.discard(s)
 
    for s in exceptionals:
        print  'handling exceptional condition for', s.getpeername()
        inputs.discard(s)
        outputs.discard(s)
        s.close()
        del http_handlers[s.fileno()]
