
from pyccn import CCN, Name, Interest, Key, ContentObject, Closure
import logging
import sys, threading, getpass, time

logging.basicConfig(filename='tyzxserver.log', level=logging.DEBUG)
log = logging.getLogger("TyzxServer")
import simplejson

import SocketServer, sys
from time import strftime

import simplejson
import random

from Tyzx import TyzxObjects, CompositeObject, BaseObject, Tracktime, Trackpoint, Worldbounds, Camerabounds, Camera


tyzxObjs = TyzxObjects()

lasttime = None 


FRESHNESS_SECONDS = 1

# this should be in PyCCN 
import struct
def versionFromTime(t):
    inttime = int(t * 4096 + 0.5)
    bintime = struct.pack("!Q", inttime)
    version = bintime.lstrip(b'\x00')
    component = b'\xfd' + version
    return component


    
class PersonTrackUDPHandler(SocketServer.BaseRequestHandler):
    PORT = 4722

    def handle(self):
        global lasttime        
        data = self.request[0].strip(" \x00")
        #T = strftime("%Y-%m-%d %H:%M:%S")
        #print "%s Received from %s:%i\n%s \n" % (T, self.client_address[0], self.client_address[1], D)
        fields = data.split()
        if fields[0]=="object":
            #print "****", fields
            bo = BaseObject(fields)
#            if bo.status=="exit":
#                try:
#                    del tyzxObjs.objs[bo.id]
#                except:   
#                    print "error deleting tyzx object"
#            else:        
            tyzxObjs.update(bo)
            print
            print "present      - ",  tyzxObjs.objs.keys()            
            print "exit cache   - ",  tyzxObjs.objExits.keys() 
        elif fields[0]=="tracktime":
            if lasttime is None:
                print "Received Tyzx time packet, ready..."
            lasttime = Tracktime(fields)
            tyzxObjs.update(lasttime)
        elif fields[0]=="trackpoint":            
            tyzxObjs.update(Trackpoint(fields))
        elif fields[0]=="worldbounds":
            print "worldbounds", Worldbounds(fields).toJSON()
        elif fields[0]=="camerabounds":
            print "camerabounds", Camerabounds(fields).toJSON()
        elif fields[0]=="camera":
            print "camera", Camera(fields).toJSON()
        else:
            print "Unrecognized message.", data
        
        self.reapExits()
        #print len(tyzxObjs.objs) #tyzxObjs.toJSON()
        

    def reapExits(self):
    
        d = set()
        for obj in tyzxObjs.objExits.values(): 
            if (time.time() > (obj.localupdatetime + 20*FRESHNESS_SECONDS)): # keep them around long enough to expire from the content store
                d.add(obj.id)
        for id in d:
            del tyzxObjs.objExits[id]
                

class TyzxServer(Closure.Closure):
    def __init__(self, prefixstr ):
        self.handle = CCN.CCN()

        #XXX: temporary, until we allow fetching key from key storage
        self.key = self.handle.getDefaultKey()
        self.keylocator = Key.KeyLocator(self.key)

        self.prefix = Name.Name(prefixstr)

#        member_name = Name.Name(self.members_uri)
#        member_name.appendKeyID(fix_digest(self.key.publicKeyID))
#        self.member_message = self.publish(member_name, nick)



    def listen(self):
        #listen to requests in namespace
        self.handle.setInterestFilter(self.prefix, self)
        self.handle.run(-1)

    def publish(self, name, content):
        # Name
        #print name
        
        

        # SignedInfo
        si = ContentObject.SignedInfo()
        si.type = ContentObject.ContentType.CCN_CONTENT_DATA
        si.finalBlockID = b'\x00'
        si.publisherPublicKeyDigest = self.key.publicKeyID
        si.keyLocator = self.keylocator
        si.freshnessSeconds = FRESHNESS_SECONDS

        # ContentObject
        co = ContentObject.ContentObject()
        co.content = content
        co.name = name
        co.signedInfo = si        
        co.sign(self.key)
        return co

    def upcall(self, kind, upcallInfo):
        global lasttime
        if lasttime is None:  # can't answer yet
            return Closure.RESULT_OK
            
        if len(tyzxObjs.objs)<1:
            return Closure.RESULT_OK
                
        interest = upcallInfo.Interest
        #print "Interest", interest.name, time.time()
        
        # CALL content matches interest to check exclusion on versions
        # 
        
        #print interest.exclude
        name = interest.name
        #print name
        if name==self.prefix:   # root 
            #print "Request for root: %s" % str(name)
            
            if interest.exclude is None:
                freshids = tyzxObjs.objs.keys()[0:1]
            else:                
                if len(interest.exclude.components) > 0:
                    ids = set(tyzxObjs.objs.keys())# new stuff we have
                    suffixes = set([int(str(s)[1:]) for s in interest.exclude.components])
                    freshids = list(ids.difference(suffixes))           # do we need this conversion?    
                    #print "ids", ids
                    #print "suffixes", suffixes                    
                    #print "freshids", freshids
                else:
                    freshids = tyzxObjs.objs.keys()[0:1]
                    

            if len(freshids)>0:
                child = freshids[0] 
            else:                 
                return Closure.RESULT_OK    # no new content
                
        else:  # should check what we're receiving! take next component

            child = int(name.components[-1:][0])   # why not be able to do this on name?
            #print "Request for child: %s" % child, time.time()
        
        #print "child - ", child           
        if tyzxObjs.objs.has_key(child):                                           
            O = tyzxObjs.objs[child]
        else:
            # Don't want to respond with a nonexistent. NDN way is to not answer interest.
            # If we've just started, we may not even know what the content store knows.
            # But, we do want to answer "exits" that we know about. 
            #print "child", child, "is not present"
            if tyzxObjs.objExits.has_key(child):
                #print "child", child, "is exited"
                O = tyzxObjs.objExits[child]
            else:
                return Closure.RESULT_OK
            
            
            #O = CompositeObject(BaseObject())
            #O.time = lasttime.time
            #O.id = int(child)
            #O.status = "nonexistent" 

        msgname = Name.Name(self.prefix)
        msgname += str(child) 
	msgname.components.append(versionFromTime (O.time))   # should have msgname.append
	msgname.ccn_data_dirty=True
# need binary add component
        self.message = self.publish(msgname, O.toJSON())
        #print "Publishing", msgname, O.toJSON()
        #print "Present:", tyzxObjs.objs.keys(), time.time()
        self.handle.put(self.message)

        return Closure.RESULT_INTEREST_CONSUMED


        return Closure.RESULT_OK
        
        

import time
if __name__ == "__main__":
    if  len(sys.argv) > 1:
        HOST = sys.argv[1]
    else:
        HOST = "" # listen on all interfaces
        

    prefix = "ccnx:/ndn/ucla.edu/apps/tv1/occupants"
    

    ndnserver = TyzxServer(prefix)
    thread = threading.Thread(target=ndnserver.listen)
    print "Starting NDN server on", prefix, "and waiting for time packet"
    thread.start()
   
    udpserver = SocketServer.UDPServer((HOST, PersonTrackUDPHandler.PORT), PersonTrackUDPHandler)
    print "Starting Tyzx socket server on", PersonTrackUDPHandler.PORT
    udpserver.serve_forever()
