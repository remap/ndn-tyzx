import SocketServer, sys
from time import strftime
        
class PersonTrackUDPHandler(SocketServer.BaseRequestHandler):
    PORT = 4722
    def handle(self):
	D = self.request[0].strip()
	T = strftime("%Y-%m-%d %H:%M:%S")
        print "%s Received from %s:%i\n%s \n" % (T, self.client_address[0], self.client_address[1], D)

if __name__ == "__main__":
    if  len(sys.argv) > 1:
        HOST = sys.argv[1]
    else:
	HOST = "" # listen on all interfaces
    server = SocketServer.UDPServer((HOST, PersonTrackUDPHandler.PORT), PersonTrackUDPHandler)
    print "Starting socket server on %i" % PersonTrackUDPHandler.PORT
    server.serve_forever()
    
