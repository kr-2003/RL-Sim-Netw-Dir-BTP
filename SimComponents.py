"""
    A bit more detailed set of components to use in packet switching
    queueing experiments.
    Copyright 2014 Greg M. Bernstein
    Released under the MIT license
"""
import random

import simpy
from Params import port_rate, numOfVOQsPerPort, numOfOutputPorts, lk_delay
from simpy.core import BoundClass
from simpy.resources import base
from heapq import heappush, heappop


class Packet(object):
    """ A very simple class that represents a packet.
        This packet will run through a queue at a switch output port.
        We use a float to represent the size of the packet in bytes so that
        we can compare to ideal M/M/1 queues.

        Parameters
        ----------
        time : float
            the time the packet arrives at the output queue.
        size : float
            the size of the packet in bytes
        id : int
            an identifier for the packet
        src, dst : int
            identifiers for source and destination
        flow_id : int
            small integer that can be used to identify a flow
    """
    def __init__(self, time, size, id, src, dst, flow_id=0, portID=None, contentionDelay=0, lookupwaitdelay =0):
        self.time = time
        self.size = size
        self.id = id
        self.src = src
        self.dst = dst
        self.flow_id = flow_id
        self.portID = portID
        self.contentionDelay = contentionDelay
        self.lookupwaitdelay = lookupwaitdelay
        self.frontpackets = 0

    def __repr__(self):
        return "time: {}, id: {}, src: {}, dst: {}, size: {}".\
            format(self.time, self.id, self.portID, self.dst, self.size)

class PacketGenerator(object):
    """ Generates packets with given inter-arrival time distribution.
        Set the "out" member variable to the entity to receive the packet.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        adist : function
            a no parameter function that returns the successive inter-arrival times of the packets
        sdist : function
            a no parameter function that returns the successive sizes of the packets
        initial_delay : number
            Starts generation after an initial delay. Default = 0
        finish : number
            Stops generation at the finish time. Default is infinite


    """
    def __init__(self, env, id,  adist, sdist,active, initial_delay=0, finish=float("inf"), flow_id=0, portID=None):
        self.id = id
        self.env = env
        self.adist = adist
        self.sdist = sdist
        self.initial_delay = initial_delay
        self.finish = finish
        self.out = None
        self.packets_sent = 0
        self.bytes_sent=0
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.flow_id = flow_id
        self.start1time= env.now
        self.active = active
        self.portID = portID

    def run(self):
        """The generator function used in simulations.
        """
        if self.active:
            while self.env.now < self.finish:
            # wait for next transmission
                yield self.env.timeout(self.adist())
                self.packets_sent += 1
#                 src= random.randrange(0,16,1)

                dst = random.randrange(0,numOfOutputPorts)
#                 dst=0
#                p = Packet(self.env.now, self.sdist, self.packets_sent, src=self.id, dst=dst,  flow_id=self.flow_id)
                p = Packet(self.env.now, self.sdist, self.packets_sent, src=self.id, dst=dst,  flow_id=self.flow_id, portID=self.portID)
                #print(p)
                self.bytes_sent+= p.size
                self.out.put(p)

class PacketSink(object):
    """ Receives packets and collects delay information into the
        waits list. You can then use this list to look at delay statistics.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        debug : boolean
            if true then the contents of each packet will be printed as it is received.
        rec_arrivals : boolean
            if true then arrivals will be recorded
        absolute_arrivals : boolean
            if true absolute arrival times will be recorded, otherwise the time between consecutive arrivals
            is recorded.
        rec_waits : boolean
            if true waiting time experienced by each packet is recorded
        selector: a function that takes a packet and returns a boolean
            used for selective statistics. Default none.

    """
    def __init__(self, env, rec_arrivals=False, absolute_arrivals=False, rec_waits=True, debug=False):
        self.store = simpy.Store(env)
        self.env = env
        self.rec_waits = rec_waits
        self.rec_arrivals = rec_arrivals
        self.absolute_arrivals = absolute_arrivals
        self.waits = []
        self.qWaits = []
        self.cWaits = []
        self.arrivals = []
        self.debug = debug
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.packets_rec = 0
        self.bytes_rec = 0
        self.fronpackets = []

    def run(self):
        while True:
            msg = yield self.store.get()
            self.packets_rec += 1
            self.bytes_rec += msg.size
            self.fronpackets.append(msg.frontpackets)
            if self.rec_waits:
                self.waits.append(self.env.now - msg.time)
                #print (self.env.now - msg.time)
                endTime = self.env.now
                genTime = msg.time
                transDelay = msg.size * 8.0 / port_rate
                contentionDelay = msg.contentionDelay
                self.cWaits.append(contentionDelay)
                #print msg.lookupwaitdelay
                if endTime - genTime - transDelay - lk_delay - contentionDelay < 0:
                    self.qWaits.append(0)
                else:
                    self.qWaits.append(endTime - genTime - transDelay - lk_delay - contentionDelay)

            if self.debug:
                print(msg)
    
    def put(self, pkt):
        self.store.put(pkt)

class VOQ(object):
    """ Models a switch output port with a given rate and buffer size limit in bytes.
        Set the "out" member variable to the entity to receive the packet.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        rate : float
            the bit rate of the port
        qlimit : integer (or None)
            a buffer size limit in bytes for the queue (does not include items in service).

    """
    def __init__(self, env, rate, qlimit, debug=False, switch_id= None, outputPorts=None, inputport_id=None):
        self.store = simpy.Store(env)
        self.rate = rate
        self.env = env
        self.out = None
        self.packets_rec = 0
        self.packets_drop = 0
        self.inputport = inputport_id
        self.qlimit = qlimit
        self.byte_size = 0  # Current size of the queue in bytes
        self.debug = debug
        self.busy = 0  # Used to track if a packet is currently being sent
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.count = 1
        self.outputPorts = outputPorts
        self.switch_id = switch_id

    def run(self):
        while True:
            msg = yield self.store.get()
            self.byte_size -= msg.size
#            # check if destination port for is free
#            # and set wait time according to it
            with self.outputPorts[self.switch_id][msg.dst].request() as req:
                t1 = self.env.now
                yield(req)
                msg.contentionDelay = self.env.now - t1
                yield self.env.timeout(msg.size * 8.0 / self.rate)
                self.out.put(msg)
            if self.debug:
                print(msg)

    def put(self, pkt):
        self.packets_rec += 1
        # find transmission delay for bits in front of queue
        #print("Switch port class put()={}".format(pkt)
        tr_delay = (self.byte_size * 8) / (self.rate)

        tmp = self.byte_size + pkt.size

        if self.qlimit is None:
            self.byte_size = tmp
            # insert delay info in packet
            pkt.delay2 = tr_delay

            return self.store.put(pkt)
        if tmp >= self.qlimit:
            self.packets_drop += 1
            return
        else:
            self.byte_size = tmp
            # insert delay info in packet
            pkt.delay2 = tr_delay

            return self.store.put(pkt)

class Port(object):
    """ Models a switch output port with a given rate and buffer size limit in bytes.
        Set the "out" member variable to the entity to receive the packet.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        rate : float
            the bit rate of the port
        qlimit : integer (or None)
            a buffer size limit in bytes for the queue (does not include items in service).

    """
    def __init__(self, env, rate, qlimit, debug=False, lookuptable=None):
        self.store = simpy.Store(env)
        self.rate = rate
        self.env = env
        self.outs = [None for _ in range(numOfVOQsPerPort)]
        self.packets_rec = 0
        self.packets_drop = 0
        self.qlimit = qlimit
        self.byte_size = 0  # Current size of the queue in bytes
        self.debug = debug
        self.lookuptable = lookuptable
        self.busy = 0  # Used to track if a packet is currently being sent
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.lk_delay = lk_delay
        # tabel lookup delay for one packet



    def run(self):
        while True:
            msg = yield self.store.get()
            msg.lookupwait = self.env.now - msg.lookupwait
            self.busy = 1
            self.byte_size -= msg.size
            with self.lookuptable.request() as req:
                t1 = self.env.now
                yield (req)
                msg.lookupwaitdelay = self.env.now - t1
                yield self.env.timeout(self.lk_delay)
            self.outs[msg.dst].put(msg)
            self.busy = 0
            if self.debug:
                print(msg)

    def put(self, pkt):
        self.packets_rec += 1
        pkt.lookupwait = self.env.now
        tmp = self.byte_size + pkt.size
        if self.qlimit is None:
            self.byte_size = tmp
            return self.store.put(pkt)
        if tmp >= self.qlimit:
            self.packets_drop += 1
            return
        else:
            self.byte_size = tmp
            return self.store.put(pkt)

class FlowDemux(object):
    """ A demultiplexing element that splits packet streams by flow_id.

    Contains a list of output ports of the same length as the probability list
    in the constructor.  Use these to connect to other network elements.

    Parameters
    ----------
    outs : List
        list of probabilities for the corresponding output ports
"""

    def __init__(self, outs=None, default=None):
        self.outs = outs
        self.default = default
        self.packets_rec = 0

    def put(self, pkt):
        self.packets_rec += 1
        flow_id = pkt.flow_id
        if flow_id < len(self.outs):
            self.outs[flow_id].put(pkt)
        else:
            if self.default:
                self.default.put(pkt)


class SinkMonitor(object):
    """ A monitor for an SwitchSink. Looks at the number of items in the SwitchPort
        in service + in the queue and records that info in the sizes[] list. The
        monitor looks at the port at time intervals given by the distribution dist.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        port : SwitchPort
            the switch port object to be monitored.
        dist : function
            a no parameter function that returns the successive inter-arrival times of the packets

    """
    def __init__(self, env, sink, dist):
        self.sink = sink
        self.env = env
        self.dist = dist
        self.sizes = []
        self.var = []
        self.previous = 0
        self.action = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.dist)
            total = self.sink.bytes_rec-self.previous
            self.sizes.append(total)
            self.previous=self.sink.bytes_rec


class TableAccessMonitor(object):
    """ A monitor for a table. Looks at the number of items in the SwitchPort
        in service + in the queue and records that info in the sizes[] list. The
        monitor looks at the port at time intervals given by the distribution dist.

        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        port : SwitchPort
            the switch port object to be monitored.
        dist : function
            a no parameter function that returns the successive inter-arrival times of the packets

    """
    def __init__(self, env, table, dist):
        self.table = table
        self.env = env
        self.dist = dist
        self.sizes = []
        self.var = []
        self.previous = 0
        self.action = env.process(self.run())

    def run(self):
        while True:
            yield self.env.timeout(self.dist)
            total = self.table.hit_count-self.previous
            self.sizes.append(total)
            self.previous=self.table.hit_count


# class WFQScheduler(object):
#     """
#         Parameters
#         ----------
#         env : simpy.Environment
#             the simulation environment
#         rate : float
#             the bit rate of the port
#         phis : A list
#             list of the phis parameters (for each possible packet flow_id). We assume a simple assignment of
#             flow id to phis, i.e., flow_id = 0 corresponds to phis[0], etc...
#     """
#     def __init__(self, env, rate, phis, debug=False):
#         self.env = env
#         self.rate = rate
#         self.phis = phis
#         self.F_times = [0.0 for i in range(len(phis))]  # Initialize all the finish time variables
#         # We keep track of the number of packets from each flow in the queue
#         self.flow_queue_count = [0 for i in range(len(phis))]
#         self.active_set = set()
#         self.vtime = 0.0
#         self.out = None
#         self.packets_rec = 0
#         self.packets_drop = 0
#         self.debug = debug
#         self.store = StampedStore(env)
#         self.action = env.process(self.run())  # starts the run() method as a SimPy process
#         self.last_update = 0.0
#
#     def run(self):
#         while True:
#             msg = (yield self.store.get())
#             self.last_update = self.env.now
#             flow_id = msg.flow_id
#             # update information about flow items in queue
#             self.flow_queue_count[flow_id] -= 1
#             if self.flow_queue_count[flow_id] == 0:
#                 self.active_set.remove(flow_id)
#             # If end of busy period, reset virtual time and reinitialize finish times.
#             if len(self.active_set) == 0:
#                 self.vtime = 0.0
#                 for i in range(len(self.F_times)):
#                     self.F_times[i] = 0.0
#             # Send message
#             yield self.env.timeout(msg.size*8.0/self.rate)
#             self.out.put(msg)
#
#     def put(self, pkt):
#         self.packets_rec += 1
#         now = self.env.now
#         flow_id = pkt.flow_id
#         self.flow_queue_count[flow_id] += 1
#         self.active_set.add(flow_id)
#         phi_sum = 0.0
#         for i in self.active_set:
#             phi_sum += self.phis[i]
#         self.vtime += (now-self.last_update)/phi_sum
#         self.F_times[flow_id] = max(self.F_times[flow_id], self.vtime) + pkt.size*8.0/self.phis[flow_id]
#         # print "Flow id = {}, packet_id = {}, F_time = {}".format(flow_id, pkt.id, self.F_times[flow_id])
#         self.last_update = now
#         return self.store.put((self.F_times[flow_id], pkt))



class WFQScheduler(object):
    """
        Parameters
        ----------
        env : simpy.Environment
            the simulation environment
        rate : float
            the bit rate of the port
        phis : A list
            list of the phis parameters (for each possible packet flow_id). We assume a simple assignment of
            flow id to phis, i.e., flow_id = 0 corresponds to phis[0], etc...
    """
    def __init__(self, env, switching_rate, debug=False):
        self.env = env
        self.rate = switching_rate
        self.F_times = [0.0 for i in range(numOfOutputPorts)]  # Initialize all the finish time variables
        # We keep track of the number of packets from each flow in the queue
        #self.flow_queue_count = [0 for i in range(len(phis))]
        self.active_set = set()
        self.vtime = 0.0
        self.outs = None
        self.packets_rec = 0
        self.packets_drop = 0
        self.debug = debug
        self.store = StampedStore(env)
        self.action = env.process(self.run())  # starts the run() method as a SimPy process
        self.last_update = 0.0

    def run(self):
        while True:
            msg = (yield self.store.get())
            self.last_update = self.env.now
            flow_id = msg.flow_id
            # update information about flow items in queue
            self.flow_queue_count[flow_id] -= 1
            if self.flow_queue_count[flow_id] == 0:
                self.active_set.remove(flow_id)
            # If end of busy period, reset virtual time and reinitialize finish times.
            if len(self.active_set) == 0:
                self.vtime = 0.0
                for i in range(len(self.F_times)):
                    self.F_times[i] = 0.0
            # Send message
            yield self.env.timeout(msg.size*8.0/self.rate)
            self.outs[msg.out_port].put(msg)

    def put(self, pkt):
        self.packets_rec += 1
        now = self.env.now
        queue_id = pkt.queue_id
        #self.flow_queue_count[flow_id] += 1
        self.active_set.add(queue_id)
        phi_sum = 0.0
        for i in self.active_set:
            phi_sum += self.phis[i]
        self.vtime += (now-self.last_update)/phi_sum
        self.F_times[flow_id] = self.F_times[flow_id]
        # print "Flow id = {}, packet_id = {}, F_time = {}".format(flow_id, pkt.id, self.F_times[flow_id])
        self.last_update = now
        return self.store.put((self.F_times[flow_id], pkt))



class StampedStorePut(base.Put):
    """ Put *item* into the store if possible or wait until it is.
        The item must be a tuple (stamp, contents) where the stamp is used to sort
        the content in the StampedStore.
    """
    def __init__(self, resource, item):
        self.item = item
        """The item to put into the store."""
        super(StampedStorePut, self).__init__(resource)


class StampedStoreGet(base.Get):
    """Get an item from the store or wait until one is available."""
    pass

class StampedStore(base.BaseResource):
    """Models the production and consumption of concrete Python objects.

    Items put into the store can be of any type.  By default, they are put and
    retrieved from the store in a first-in first-out order.

    The *env* parameter is the :class:`~simpy.core.Environment` instance the
    container is bound to.

    The *capacity* defines the size of the Store and must be a positive number
    (> 0). By default, a Store is of unlimited size. A :exc:`ValueError` is
    raised if the value is negative.

    """
    def __init__(self, env, capacity=float('inf')):
        super(StampedStore, self).__init__(env, capacity=float('inf'))
        if capacity <= 0:
            raise ValueError('"capacity" must be > 0.')
        self._capacity = capacity
        self.items = []  # we are keeping items sorted by stamp
        self.event_count = 0 # Used to break ties with python heap implementation
        # See: https://docs.python.org/3/library/heapq.html?highlight=heappush#priority-queue-implementation-notes
        """List of the items within the store."""

    @property
    def capacity(self):
        """The maximum capacity of the store."""
        return self._capacity

    put = BoundClass(StampedStorePut)
    """Create a new :class:`StorePut` event."""

    get = BoundClass(StampedStoreGet)
    """Create a new :class:`StoreGet` event."""

    # We assume the item is a tuple: (stamp, packet). The stamp is used to
    # sort the packet in the heap.
    def _do_put(self, event):
        self.event_count += 1 # Needed this to break heap ties
        if len(self.items) < self._capacity:
            heappush(self.items, [event.item[0], self.event_count, event.item[1]])
            event.succeed()

    # When we return an item from the stamped store we do not
    # return the stamp but only the content portion.
    def _do_get(self, event):
        if self.items:
            event.succeed(heappop(self.items)[2])

