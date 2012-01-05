import simplejson, time    
    
class TyzxObject(object):
    def __init__(self):
        object.__init__(self)
        T = time.time()
        self.localcreatetime = T
        self.localupdatetime = T
        self.lastinteresttime = 0 
    def toJSON(self):
        return simplejson.dumps(self.__dict__)
    def fromJSON(self, json):
        try:       
            d = simplejson.loads(json)        
        except:
            print "TyzxObject.fromJSON error parsing", json
            return
        for f in d:
            setattr(self, f, d[f]) 
        

class CompositeObject(TyzxObject):
    def __init__(self, tobj):
        TyzxObject.__init__(self)
        self.updateObject(tobj)
        self.x = 0 
        self.y = 0
        self.z = 0
    def updateTracktime(self, tt):
        self.time = tt.time
	self.localupdatetime = tt.time
        self.count = tt.count
    def updateTrackpoint(self, tp):
        self.x = tp.x
        self.y = tp.y
        self.z = tp.z
        self.status = "present"
    def updateObject(self,tobj):   
        self.time = tobj.time
        self.count = -1
        self.id = int(tobj.id)
        self.status = tobj.status
   # Refactor to updateAll? 

class BaseObject(TyzxObject):
    def __init__(self, initfields=[]):   
        TyzxObject.__init__(self)
        if len(initfields)>3: 
            try:
                self.parseFields(initfields)
            except:
                print "BaseObject, error parsing init fields", initfields
        else:
            self.time = -1
            self.id = -1
            self.status = ""
    def parseFields(self, f):
        self.time = float(f[3])
        self.id = int(f[1])
        self.status = f[2]        

class Tracktime(TyzxObject):
    def __init__(self, initfields=[]):
        TyzxObject.__init__(self)
        if len(initfields)>2: 
            try:
                self.parseFields(initfields)
            except:
                print "Tracktime, error parsing init fields", initfields
        else:
            self.time = -1
            self.count = -1
    def parseFields(self, f):
        self.time = float(f[2])
        self.count = long(f[1])

class Trackpoint(TyzxObject):
    def __init__(self, initfields=[]):
        TyzxObject.__init__(self)
        if len(initfields)>4: 
            try:
                self.parseFields(initfields)
            except:
                print "Trackpoint, error parsing init fields", initfields
        else:
            self.id = -1             #Object id
            self.x = 0 
            self.y = 0
            self.z = 0
    def parseFields(self, f):
            self.id = int(f[1])     
            self.x = float(f[2])
            self.y = float(f[3])
            self.z = float(f[4])   

class Camerabounds(TyzxObject):
    def __init__(self, initfields=[]):
        TyzxObject.__init__(self)
        if len(initfields)>5: 
            try:
                self.parseFields(initfields)
            except:
                print "Camerabounds, error parsing init fields", initfields
        else:
            self.id = int(-1)
            self.boundnum = -1
            self.x = 0
            self.y = 0      
    def parseFields(self, f):
            self.id = int(f[1])
            self.boundnum = int(f[2])
            self.x = float(f[3])
            self.y = float(f[3])
            
class Worldbounds(TyzxObject):
    def __init__(self, initfields=[]):
        TyzxObject.__init__(self)
        if len(initfields)>6: 
            try:
                self.parseFields(initfields)
            except:
                print "Worldbounds, error parsing init fields", initfields
        else:
            self.x1 = 0
            self.y1 = 0
            self.x2 = 0
            self.y2 = 0
    def parseFields(self, f):
            self.x1 = float(f[1])
            self.y1 = float(f[2])
            self.x2 = float(f[3])
            self.y2 = float(f[4])

class Camera(TyzxObject):
    def __init__(self, initfields=[]):
        TyzxObject.__init__(self)
        if len(initfields)>15: 
            try:
                self.parseFields(initfields)
            except:
                print "Camera, error parsing init fields", initfields
        else:
            self.time = -1
            self.id = -1 
            self.online = -1
            self.name = ""
            self.x = 0
            self.y = 0
            self.height = 0 
            self.thetaX = 0 
            self.thetaY = 0 
            self.thetaZ = 0 
            self.cX = 0
            self.cY = 0
            self.cZ = 0 
            self.imageWidth = 0
            self.imageHeight = 0
    def parseFields(self, f):            
            self.id = int(f[1])
            self.online = long(f[2])
            self.name = f[3]
            self.time = float(f[4])
            self.x = float(f[5])
            self.y = float(f[6])
            self.height = float(f[7])            
            self.thetaX = float(f[8])             
            self.thetaY = float(f[9])             
            self.thetaZ = float(f[10])             
            self.cX = float(f[11])            
            self.cY = float(f[12])            
            self.cZ = float(f[13])            
            self.imageWidth = float(f[14])            
            self.imageHeight = float(f[15])            
            
            
class TyzxObjects(object):
    def __init__(self):
        object.__init__(self)
        self.objs= {}
        self.objExits = {}
        self.lasttime = Tracktime()
    def update(self, obj):
        obj.localupdatetime = time.time()
        if isinstance(obj, CompositeObject):
            self.objs[obj.id] = obj
        if isinstance(obj, BaseObject):
            if self.objs.has_key( obj.id ):
                self.objs[obj.id].updateObject(obj) # new object should have status = exit
                if obj.status=="exit": 
                    self.objExits[obj.id] = self.objs[obj.id]
                    del self.objs[obj.id]
            else:
                self.objs[obj.id] = CompositeObject(obj)
        if isinstance(obj, Tracktime):
            self.lasttime = obj
        if isinstance(obj, Trackpoint):
            if self.objs.has_key( obj.id ):        
                self.objs[obj.id].updateTrackpoint(obj)                            
                self.objs[obj.id].updateTracktime(self.lasttime)
            else:  # make an object, the system has already started
                co = CompositeObject(BaseObject())
                co.id = obj.id 
                co.updateTracktime(self.lasttime)
                co.updateTrackpoint(obj) 
                self.objs[obj.id] = co 
                #print "TyzxObjects Tried to update Trackpoint/time for object id not stored.", obj.id

    def toJSON(self):
        s="{ \"present\": {"
        for obj in self.objs.values():
            s+=obj.toJSON()+"," 
        s+="},"
        s+=" \"exit\": {" 
        for obj in self.objExits.values():
            s+=obj.toJSON()+"," 
        s+="} }"
        return s
            
    def delete(self, obj):
        try:
            del self.objs[obj.id]
        except:
            print "TyzxObjects Could not delete.", obj.id
        
    def get(self, id):
        return self.objs[id]
        
    
    
    
