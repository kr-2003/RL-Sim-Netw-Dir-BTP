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
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
GRAY = (100, 100, 100)

# Initialize the game window
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Data Center Topology Visualization")

class Packet:
    def __init__(self, path):
        self.path = path
        self.current_index = 0
        self.x, self.y = path[0].x, path[0].y
        self.speed = 2  # Adjust the speed of the packet here

    def move(self):
        if self.current_index < len(self.path) - 1:
            next_node = self.path[self.current_index + 1]
            dx = next_node.x - self.x
            dy = next_node.y - self.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance > 0:
                self.x += self.speed * dx / distance
                self.y += self.speed * dy / distance

                # Check if packet has reached the next node
                if abs(self.x - next_node.x) < 1 and abs(self.y - next_node.y) < 1:
                    self.current_index += 1
                    self.x, self.y = next_node.x, next_node.y

    def draw(self, screen):
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y)), 5)

# Define Node class for pygame
class Node:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (self.x, self.y), NODE_RADIUS, 0, draw_top_right=True, draw_top_left=True, draw_bottom_left=True, draw_bottom_right=True)

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
        self.populate_nodes()
        self.packet = None
        self.find_path_and_init_packet()

    def populate_nodes(self):
        # Create node objects for pygame
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
                color = BLACK  # server

            # Create the node and update position trackers
            self.nodes[node] = Node(x, y, color)
            x_positions[node.nodeType] += 4 * NODE_RADIUS

        # Prepare edges for rendering
        for edge in self.network.edges:
            node1, node2 = self.nodes[edge[0]], self.nodes[edge[1]]
            self.edges.append(Edge(node1, node2))

    def find_path_and_init_packet(self):
        # Determine the shortest path from a core switch to Server 1
        core_switch = next(node for node in self.nodes if node.nodeType == 'cs')
        server_1 = next(node for node in self.nodes if node.nodeType == 'server' and node.index == 1)
        path = nx.shortest_path(self.network, source=core_switch, target=server_1)

        # Convert path to a list of Node objects for pygame
        path_nodes = [self.nodes[node] for node in path]
        self.packet = Packet(path_nodes)

    def draw(self, screen):
        # Draw edges
        for edge in self.edges:
            edge.draw(screen)

        # Draw nodes
        for node in self.nodes.values():
            node.draw(screen)

        # Draw and move the packet
        if self.packet:
            self.packet.move()
            self.packet.draw(screen)

def main():
    k = 4
    network = nx.Graph()
    dc_topology(network, k)

    game = Game(network)

    clock = pygame.time.Clock()
    running = True
    while running:
        screen.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Draw the topology and animate packet movement
        game.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == '__main__':
    main()
