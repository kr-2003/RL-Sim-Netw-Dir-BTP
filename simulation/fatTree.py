import networkx as nx
from models import *
from itertools import islice


def dc_topology(network,k2):
    for dc_id in range(1):
        servers = []
        coreSwitches_bdc = [Switch(nodeType='cs', index=index, network=network, DcID=dc_id) for index in
                            range(int((k2 / 2) ** 2))]
        aggSwitches_bdc = []
        edgeSwitches_bdc = []

        for podId in range(k2):
            for index in range(int(k2 / 2)):
                aggSwitches_bdc.append(Switch(nodeType='as', pod=podId, index=index, network=network, DcID=dc_id))
                edgeSwitches_bdc.append(Switch(nodeType='es', pod=podId, index=index, network=network, DcID=dc_id))
            for index in range(int(k2 / 2) ** 2):
                # if(podId!=0): #only append servers with podid not equal to zero
                servers.append(Server(pod=podId, index=index, network=network, DcID=dc_id))

        # add nodes
        network.add_nodes_from(coreSwitches_bdc + aggSwitches_bdc + edgeSwitches_bdc + servers)

        # add edges
        for podId in range(k2):
            i = 0
            for aSwitch in [n for n in network.nodes(False) if
                            (n.nodeType == 'as' and n.pod == podId and n.DcID == dc_id)]:
                l = 0
                for j in range(i, int(k2 / 2 + i)):
                    # add core to agg
                    cSwitch = [n for n in network.nodes(False) if
                               (n.nodeType == 'cs' and n.index == j and n.DcID == dc_id)]
                    network.add_edge(aSwitch, cSwitch[0])
                    l = j
                i = l + 1

        for podId in range(k2):
            for eSwitch in [n for n in network.nodes(False) if
                            (n.nodeType == 'es' and n.pod == podId and n.DcID == dc_id)]:
                # add edge to agg
                for aSwitch in [n for n in network.nodes(False) if
                                (n.nodeType == 'as' and n.pod == podId and n.DcID == dc_id)]:
                    network.add_edge(aSwitch, eSwitch)

                # add edge to servers and for pod 0 add directly to outside edge switch

                for i in range(0, int(k2 / 2)):
                    server = [n for n in network.nodes(False) if
                              (
                                          n.nodeType == 'server' and n.pod == podId and n.index == i + eSwitch.index * k2 / 2 and n.DcID == dc_id)]
                    network.add_edge(eSwitch, server[0])

    # now make port to [port connections between links
    for edge in network.edges:
        p1 = [port1 for port1 in edge[0].ports if port1.sendDst == None]
        p2 = [port2 for port2 in edge[1].ports if port2.sendDst == None]
        p1[0].sendDst = p2[0]
        p2[0].sendDst = p1[0]



def k_shortest_paths(G, source, target, k, weight=None):
  return list(islice(nx.shortest_simple_paths(G, source, target, weight=weight), k))



def main():
    k = 4
    network = nx.Graph()
    dc_topology(network,k)
    print(network)

if __name__ == '__main__':
    count = 0
    main()