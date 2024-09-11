import pygame
import networkx as nx
from models import *  # Assuming you have defined the Switch and Server models
from itertools import islice
from fatTree import dc_topology  

# Initialize Pygame
pygame.init()

# Constants
WIDTH, HEIGHT = 1200, 600
NODE_RADIUS = 15
FPS = 300
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)
YELLOW = (255, 255, 0)

# Initialize the game window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Data Center Topology Visualization")
class Packet:
    def __init__(self, node):
        self.x, self.y = node.x, node.y  # Start packet at the initial node's position
        self.speed = 2  # Increase speed for faster movement
        self.target_node = node  # The target node the packet is moving towards
        self.latency = 0
        self.reached_target = True  # Flag to check if the packet has reached the target node

    
    def move(self, action):
        next_node = action
        dx = next_node.x - self.x
        dy = next_node.y - self.y
        distance = (dx**2 + dy**2) ** 0.5

        if distance > 0:
            self.x += self.speed * dx / distance
            self.y += self.speed * dy / distance
            self.latency += 1

        if abs(self.x - next_node.x) < 1 and abs(self.y - next_node.y) < 1:
            self.x, self.y = next_node.x, next_node.y
            self.target_node = next_node

    def draw(self, screen):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), 5)

# Define Node class for pygame
class Node:
    def __init__(self, x, y, color, nodeType):
        self.x = x
        self.y = y
        self.color = color
        self.nodeType = nodeType

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), NODE_RADIUS)

# Define Edge class for pygame
class Edge:
    def __init__(self, node1, node2, color=GRAY):
        self.node1 = node1
        self.node2 = node2
        self.color = color

    def draw(self, screen):
        pygame.draw.aaline(screen, self.color, (self.node1.x, self.node1.y), (self.node2.x, self.node2.y))

# Define Game class to handle the visualization
class Game:
    def __init__(self, network):
        self.network = network
        self.nodes = {}
        self.edges = []
        self.possible_actions = {}
        self.clock = pygame.time.Clock()
        self.time = pygame.time
        self.populate_nodes()
        self.packet = Packet(self.nodes[next(node for node in self.nodes if node.nodeType == 'cs')])
        # self.initial()

    def reset(self):
        self.packet = Packet(self.nodes[next(node for node in self.nodes if node.nodeType == 'cs')])
        self.packet.latency = 0

    def populate_nodes(self):
        spacing_y = HEIGHT // 6

        # Define the number of nodes in each layer
        layer_nodes = {
            'cs': sum(1 for n in self.network.nodes if n.nodeType == 'cs'),
            'as': sum(1 for n in self.network.nodes if n.nodeType == 'as'),
            'es': sum(1 for n in self.network.nodes if n.nodeType == 'es'),
            'server': sum(1 for n in self.network.nodes if n.nodeType == 'server')
        }

        # Calculate x starting positions for each layer to make them center-aligned
        x_positions = {
            'cs': (WIDTH - (layer_nodes['cs'] * (4 * NODE_RADIUS))) // 2,
            'as': (WIDTH - (layer_nodes['as'] * (4 * NODE_RADIUS))) // 2,
            'es': (WIDTH - (layer_nodes['es'] * (4 * NODE_RADIUS))) // 2,
            'server': (WIDTH - (layer_nodes['server'] * (4 * NODE_RADIUS))) // 2
        }
        y_positions = {
            'cs': spacing_y,
            'as': 2 * spacing_y,
            'es': 3 * spacing_y,
            'server': 4 * spacing_y
        }

        # Populate nodes in the network
        for node in self.network.nodes:
            x = x_positions[node.nodeType]
            y = y_positions[node.nodeType]
            if node.nodeType == 'cs':
                color = RED
            elif node.nodeType == 'as':
                color = BLUE
            elif node.nodeType == 'es':
                color = GREEN
            else:
                color = YELLOW  # server

            self.nodes[node] = Node(x, y, color, node.nodeType)
            x_positions[node.nodeType] += 4 * NODE_RADIUS

        # Prepare edges for rendering
        for edge in self.network.edges:
            node1, node2 = self.nodes[edge[0]], self.nodes[edge[1]]
            self.edges.append(Edge(node1, node2))

        for node in self.nodes:
            neighbours = list(self.network.neighbors(node))
            self.possible_actions[self.nodes[node]] = [self.nodes[neighs] for neighs in neighbours]

    def draw(self, screen):
        # Redraw background, nodes, and edges to avoid trailing packets
        screen.fill(WHITE)

        # Draw edges
        for edge in self.edges:
            edge.draw(screen)

        # Draw nodes
        for node in self.nodes.values():
            node.draw(screen)

        # Draw packet
        if self.packet:
            self.packet.draw(screen)

    def play_step(self, action):
        # Move the packet
        self.packet.move(action)

        # Draw everything
        self.draw(screen)
        pygame.display.flip()
        self.clock.tick(FPS)

        reward, done = 0, False
        if action.nodeType == 'server':
            reward = -self.packet.latency
            done = True

        return reward, done
    
    def initial(self):
        while True:
            # Simulate moving to an action (as an example)
            self.play_step(self.nodes[next(node for node in self.nodes if node.nodeType == 'as')])

def main():
    k = 4
    network = nx.Graph()
    dc_topology(network, k)

    game = Game(network)

    while True:
        game.play_step(game.nodes[next(node for node in game.nodes if node.nodeType == 'as')])

    pygame.quit()

if __name__ == '__main__':
    main()