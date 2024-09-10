k = 32
class Switch(object):
    '''Defines a core/aggregate/ToR switch in the DC'''

    def __init__(self, nodeType, pod=None, index=None, network=None, DcID = None):

        self.nodeType = nodeType
        self.pod = pod
        self.index = index
        self.name = 'switch'
        self.rate =  10000
        self.ports = []
        for portID in range(k):
            self.ports.append(Port(self,portID,self.rate,network))
        self.network = network
        self.DcID = DcID


    def __repr__(self):
        return ('' if self.pod == None else str(self.pod) + '.') + self.nodeType + '.' + str(self.index)+ '#'+str(self.DcID)


class EdgeSwitch(object):
    def __init__(self, nodeType, pod=None, index=None, network=None, DcID=None):
        self.nodeType = nodeType
        self.pod = pod
        self.index = index
        self.name = 'switch'
        self.rate = 10000
        self.ports = []
        for portID in range(220):
            self.ports.append(Port(self, portID, self.rate, network))
        self.network = network
        self.DcID = DcID

    def __repr__(self):
        return ('' if self.pod == None else str(self.pod) + '.') + self.nodeType + '.' + str(self.index) + '#' + str(
            self.DcID)


class Port(object):

    def __init__(self,parent,portid, rate,network):
        self.portID = portid
        self.sendavailableBW = rate
        self.recavailableBW = rate
        self.network = network
        self.sendDst = None
        self.parent = parent

class Server:
    def __init__(self, pod=None, index=None, network=None, DcID=None):
        self.nodeType = 'server'
        self.noOfVNFs = 4
        self.hostedVNFs = []
        self.BWCapacity = 10000       #in Mbps
        self.remainingBW = self.BWCapacity
        self.processingCapacity = 10000
        self.remainingcapacity = self.processingCapacity
        self.pod = pod
        self.index = index
        self.name = 'server'
        self.rate = 10000
        self.DcID = DcID
        self.ports = []
        for portID in range(1):
            self.ports.append(Port(self, portID, self.rate, network))
        self.network = network