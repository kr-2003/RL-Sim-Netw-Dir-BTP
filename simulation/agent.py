import torch
import random
import numpy as np
from collections import deque
from game import Game
from rlModel import Linear_QNet, QTrainer
from helper import plot
import networkx as nx
from fatTree import dc_topology
import time

MAX_MEMORY = 100_000
BATCH_SIZE = 1000
LR = 0.001

class Agent:

    def __init__(self):
        self.n_games = 0
        self.epsilon = 0  # randomness
        self.gamma = 0.9  # discount rate
        self.memory = deque(maxlen=MAX_MEMORY)  # popleft()
        self.model = Linear_QNet(2, 2, 4)
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma)

    def get_state(self, game):
        current_node = game.packet.target_node
        state = current_node
        return current_node, np.array([state.x, state.y])

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))  # popleft if MAX_MEMORY is reached

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE)  # list of tuples
        else:
            mini_sample = self.memory
        states, actions, rewards, next_states, dones = zip(*mini_sample)
        self.trainer.train_step(states, actions, rewards, next_states, dones)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, node, state, game):
    # Increase exploration in the early stages
      self.epsilon = max(80 - self.n_games, 10)  # Ensure epsilon doesn't go below a minimum threshold
      final_move = None
      all_possible_moves = game.possible_actions[node]

      if random.randint(0, 200) < self.epsilon:
        move = random.choice(all_possible_moves)
        final_move = all_possible_moves.index(move)
      else:
        prediction = self.model(torch.tensor(state, dtype=torch.float))
        move = torch.argmax(prediction).item()
        final_move = move

      print(f"Action chosen: {final_move}")
      return final_move
def train():
    k = 4
    network = nx.Graph()
    dc_topology(network, k)
    plot_scores = []
    plot_mean_scores = []
    total_score = 0
    record = 1000000
    agent = Agent()
    game = Game(network)

    

    while True:
        
        node_old, state_old = agent.get_state(game)
        final_move = agent.get_action(node_old, state_old, game)

        if node_old.nodeType == 'server':
            node = game.possible_actions[node_old][0]
        else:
            node = game.possible_actions[node_old][final_move]

        done=False
        while node_old == game.packet.target_node and not done:
            print(f"Moving packet: Current Node: {node_old}, Target Node: {game.packet.target_node}")
            reward, done = game.play_step(node)


            node_new, state_new = agent.get_state(game)
            agent.train_short_memory(state_old, final_move, reward, state_new, done)
            agent.remember(state_old, final_move, reward, state_new, done)

        if done:
                game.reset()
                agent.n_games += 1
                agent.train_long_memory()

                if reward < record:
                    record = reward
                    agent.model.save()

                print(f'Game {agent.n_games}, Latency: {reward}, Record: {record}')

                plot_scores.append(reward)
                total_score += reward
                mean_score = total_score / agent.n_games
                plot_mean_scores.append(mean_score)    

if __name__ == '__main__':
    train()
