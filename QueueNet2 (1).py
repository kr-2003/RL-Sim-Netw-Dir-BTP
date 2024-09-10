import functools
import random
import numpy as np
import simpy
from Params import *
from simpy.resources.resource import Resource
from SimComponents import PacketGenerator, PacketSink, VOQ, Port, SinkMonitor, FlowDemux


def expArrivals():  # Constant arrival distribution for generator
    return (mean_pkt_size * 8/gen_rate)    # in seconds
adist = functools.partial(random.expovariate, (gen_rate/(mean_pkt_size*8)))
x = [0]*numOfInputPorts
for numOfGenerators in range(num_gen):
    x[numOfGenerators] = 1
#sys.stdout = open('simulation_output.txt', 'a')
env = simpy.Environment()


inputPorts = [[None] * numOfInputPorts for _ in range(num_of_switches)]
#outputPorts = [[None] * numOfOutputPorts for _ in range(num_of_switches)]
voq = [[[None] * numOfVOQsPerPort for _ in range(numOfInputPorts)] for _ in range(num_of_switches)]
outputPorts = [[Resource(env, capacity=1) for _ in range(numOfOutputPorts)] for _ in range(num_of_switches)]
lookuptable = [[Resource(env, capacity=1) for _ in range(numOfInputPorts)]  for _ in range(num_of_switches)]
WFQSchedulers = [[None for _ in range(numOfOutputPorts)] for _ in range(num_of_switches)]
demux = FlowDemux()
pg = [None for _ in range(numOfInputPorts)]    # list that contains packet generator threads
ps = PacketSink(env, debug=False, rec_waits=True)
pm = SinkMonitor(env, ps, 1)

for switch_num in range(num_of_switches):
    for inputPortID in range(numOfInputPorts):
        inputPorts[switch_num][inputPortID] = Port(env, port_rate, qlimit_edgeports, lookuptable=lookuptable[switch_num][inputPortID])
        if switch_num == 0: #first switch
            pg[inputPortID] = PacketGenerator(env, "SJSU1", adist, sdist, x[inputPortID], portID=inputPortID)    # this line will envoke packet generatpr that will generate packet and put in to on eof the input ports of the switch
        #pg[inputPortID] = PacketGenerator(env, "SJSU1", expArrivals, sdist, x[inputPortID], portID=inputPortID)
            pg[inputPortID].out = inputPorts[switch_num][inputPortID]


for switch_num in range(num_of_switches):
    for inputPortID in range(numOfInputPorts):
        for voqID in range(numOfVOQsPerPort):
                voq[switch_num][inputPortID][voqID] = VOQ(env, port_rate, qlimit_voq, switch_id=switch_num, outputPorts=outputPorts, inputport_id=inputPortID)
                inputPorts[switch_num][inputPortID].outs[voqID] =  voq[switch_num][inputPortID][voqID]
                voq[switch_num][inputPortID][voqID].out = outputPorts[switch_num][inputPortID]
                #WFQSchedulers[switch_num][inputPortID] = WFQScheduler(env, expArrivals)
                # voq[switch_num][inputPortID][voqID].out = WFQSchedulers[switch_num][inputPortID]
                # WFQSchedulers[switch_num][inputPortID].out = demux[switch_num][inputPortID]
        if switch_num == 0:
            outputPorts[switch_num][inputPortID].out = inputPorts[switch_num+1][inputPortID]
        else:
            demux.out = ps


env.run(until=sim_time)

totalPktsGenerated = sum(pg[pktGenID].packets_sent for pktGenID in range(numOfInputPorts))
totalPktsRecdAcrossAllPorts = sum(inputPorts[switch_id][inputPortID].packets_rec for inputPortID in range(numOfInputPorts) for switch_id in range(num_of_switches))
totalPktsDroppedAcrossAllPorts = sum(inputPorts[switch_id][inputPortID].packets_drop for inputPortID in range(numOfInputPorts) for switch_id in range(num_of_switches))
totalPktsRecdAcrossAllVOQs = sum(voq[switch_id][inputPortID][VOQid].packets_rec for inputPortID in range(numOfInputPorts) for VOQid in range(numOfVOQsPerPort) for switch_id in range(num_of_switches))
totalPktsDroppedAcrossAllVOQs = sum(voq[switch_id][inputPortID][VOQid].packets_drop for inputPortID in range(numOfInputPorts) for VOQid in range(numOfVOQsPerPort) for switch_id in range(num_of_switches))

print('List of parameters:')
print("\tNumber of active input inputPorts = {}".format(x.count(1)))
print("\tInput data rate = {}".format(port_rate))
print("\tInput avg. packet size = {} bytes".format(mean_pkt_size))
print("\t1st level buffer size = {} packets".format(int(qlimit_edgeports/mean_pkt_size)))
print("\tVOQ buffer size = {} packets".format(int(qlimit_voq/mean_pkt_size)))

print('Results:')
print("\tTotal packets  generated = {}".format(totalPktsGenerated))
print("\tTotal packets received and dropped across all inputs inputPorts = {}, {}".format(totalPktsRecdAcrossAllPorts, totalPktsDroppedAcrossAllPorts))
print("\tTotal packets received and dropped across all VOQs = {}, {}".format(totalPktsRecdAcrossAllVOQs, totalPktsDroppedAcrossAllVOQs))
print("\tTotal packets received at sink = {}".format(ps.packets_rec))
print("\tAvg. port to port latency = {}".format(np.mean(ps.waits)))
print("\tAvg Throughput in bits= {}".format(np.mean(pm.sizes)*8))
print("\tAvg. contention wait at voq  = {}".format(np.mean(ps.cWaits)))
print("\tAvg. input buffer wait  = {}".format(np.mean(ps.qWaits)))
#print(ps.fronpackets[100])
#print(pm.sizes)
print("----------------------------------------------------------------------------------------------------")
#print(mean_pkt_size, 55*6.5*10**-9, np.mean(ps.qWaits), np.mean(ps.cWaits), mean_pkt_size*8/port_rate, np.mean(ps.waits))