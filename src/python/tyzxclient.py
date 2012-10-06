import time, struct
import pyccn
from pyccn import CCN, Name, Interest, Key, ContentObject, Closure, KeyLocator, ExclusionFilter
from Tyzx import CompositeObject, BaseObject

prefix = "ccnx:/ndn/ucla.edu/apps/tv1/occupants"        

DISCOVER_INTEREST_PERIOD = 0.250    # How often 
UPDATE_INTEREST_PERIOD = 0.250   
CCN_WAIT_TIME_MS = 1
        
tyzxObjects = {}    
oldObjects = set()    # still may be in the content store

ccn = CCN()

interestDiscover = Interest()
interestDiscover.name = Name(prefix)
interestDiscover.minSuffixComponents = 2   # occupant id + the implicit digest at a minimum

interestUpdate = Interest()
interestUpdate.minSuffixComponents = 2   # time (version) + the implicit digest
interestUpdate.childSelector = 1         # rightmost child
#interestUpdate.interestLifetime = ???? 

lastdiscovertime = 0     

def versionFromTime(t):
    bintime = struct.pack("!Q", int(t * 4096 + 0.5))
    version = bintime.lstrip(b'\x00')
    return b'\xfd' + version
last_version_marker = '\xfe\x00\x00\x00\x00\x00\x00'

class ProcessIncoming(Closure):

    def upcall(self, kind, upcallInfo):
        global lastdiscovertime
    
        if kind==pyccn.UPCALL_INTEREST_TIMED_OUT:            
            interest = upcallInfo.Interest 
            if len(interestDiscover.name)==len(interest.name): return pyccn.RESULT_OK   # Occupants timeout
            reqid = str(interest.name.components[-1])     # should we really need to strip? 
            if tyzxObjects.has_key(reqid): print "Timeout", reqid, "deleting..."             
            self.delObj(reqid)
            return pyccn.RESULT_OK
        elif kind==pyccn.UPCALL_CONTENT_UNVERIFIED: 
            print "Content object is unverified for", key
        elif kind==pyccn.UPCALL_CONTENT:
            try:             
                O = CompositeObject(BaseObject())
                O.fromJSON(upcallInfo.ContentObject.content)
            except:
                print "Error converting content to object."
                return pyccn.RESULT_OK
            #print upcallInfo.ContentObject.name.components
	    #print upcallInfo.ContentObject.content
            key = str(O.id)
            if O.status=="exit":            
                self.delObj(key)
            else:
                if tyzxObjects.has_key(key):            
                    tyzxObjects[key].updateObject(O)
		    tyzxObjects[key].updateTrackpoint(O)
		    tyzxObjects[key].updateTracktime(O)
                else:             
                    tyzxObjects[key] = O                  
                    lastdiscovertime = 0 
            self.printPresent()
            # ** PARSE OR USE O.toJSON() here ** 
        return pyccn.RESULT_OK

    def delObj(self, key):
        oldObjects.add(key)
        if tyzxObjects.has_key(key):
            del tyzxObjects[key]        
            
    def printPresent(self):
        print
        for obj in tyzxObjects.values():
            print obj.id,":", obj.x, obj.y, obj.z, obj.localupdatetime

if __name__ == "__main__":
    print "prefix", prefix
    processIncoming = ProcessIncoming()        
    while (True):        
        T = time.time()
        if T-lastdiscovertime > DISCOVER_INTEREST_PERIOD:
            interestDiscover.exclude = ExclusionFilter()
            interestDiscover.exclude.add_names([Name([key]) for key in tyzxObjects.keys()])
            interestDiscover.exclude.add_names([Name([key]) for key in oldObjects]) 
            ccn.expressInterest(interestDiscover.name, processIncoming, interestDiscover) 
            lastdiscovertime = time.time()        
        for obj in tyzxObjects.values():
            if T-obj.lastinteresttime < UPDATE_INTEREST_PERIOD:
                continue
            interestUpdate.name = Name(prefix)    
            interestUpdate.name += str(obj.id) 
            interestUpdate.exclude = ExclusionFilter()
            interestUpdate.exclude.add_any()
            n = Name.Name()
            n.components.append(versionFromTime(obj.time))                
            interestUpdate.exclude.add_name(n)
	    interestUpdate.exclude.add_name(Name.Name([last_version_marker]))
	    interestUpdate.exclude.add_any() 
            ccn.expressInterest(interestUpdate.name, processIncoming, interestUpdate)         
            obj.lastinteresttime = time.time()
        ccn.run(CCN_WAIT_TIME_MS)

