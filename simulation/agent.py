import torch
import random
import numpy as np
from collections import deque
from game import Game
from rlModel import Linear_QNet, QTrainer
from helper import plot
import networkx as nx
from fatTree import dc_topology

MAX_MEMORY = 100_000
BATCH_SIZE = 1000
LR = 0.001

class Agent:

    def __init__(self):
        self.n_games = 0
        self.epsilon = 0 # randomness
        self.gamma = 0.9 # discount rate
        self.memory = deque(maxlen=MAX_MEMORY) # popleft()
        self.model = Linear_QNet(2, 2, 2)
        self.trainer = QTrainer(self.model, lr=LR, gamma=self.gamma)


    def get_state(self, game):
        current_node = game.packet.target_node

        state = current_node

        return current_node, np.array([state.x, state.y])

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done)) # popleft if MAX_MEMORY is reached

    def train_long_memory(self):
        if len(self.memory) > BATCH_SIZE:
            mini_sample = random.sample(self.memory, BATCH_SIZE) # list of tuples
        else:
            mini_sample = self.memory

        states, actions, rewards, next_states, dones = zip(*mini_sample)
        self.trainer.train_step(states, actions, rewards, next_states, dones)
        #for state, action, reward, nexrt_state, done in mini_sample:
        #    self.trainer.train_step(state, action, reward, next_state, done)

    def train_short_memory(self, state, action, reward, next_state, done):
        self.trainer.train_step(state, action, reward, next_state, done)

    def get_action(self, node, state, game):
        # random moves: tradeoff exploration / exploitation
        self.epsilon = 80 - self.n_games
        final_move = None
        all_possible_moves_at_current_state = game.possible_actions[node]
        if random.randint(0, 200) < self.epsilon:
            move = random.choice(all_possible_moves_at_current_state)
            final_move = all_possible_moves_at_current_state.index(move)
        else:
            # print(state)
            prediction = self.model(torch.tensor(state, dtype=torch.float))
            move = torch.argmax(prediction).item()
            # print(move)
            final_move = move

        print(final_move)
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
        game.clock.tick(60)
        final_move = agent.get_action(node_old, state_old, game)
        game.play_step(game.nodes[next(node for node in game.nodes if node.nodeType == 'as')])

        # get old state
        # node_old, state_old = agent.get_state(game)

        # # get move
        # final_move = agent.get_action(node_old, state_old, game)

        # node = game.possible_actions[node_old][final_move]
        # print(node_old.nodeType)
        # print(node.nodeType)

        # # perform move and get new state
        # reward, done = game.play_step(node)
        # node_new, state_new = agent.get_state(game)

        # # train short memory
        # agent.train_short_memory(state_old, final_move, reward, state_new, done)

        # # remember
        # agent.remember(state_old, final_move, reward, state_new, done)

        # print(done)

        # if done:
        #     # train long memory, plot result
        #     game.reset()
        #     agent.n_games += 1
        #     agent.train_long_memory()

        #     if reward < record:
        #         record = reward
        #         agent.model.save()

        #     print('Game', agent.n_games, 'Latency', reward, 'Record:', record)

        #     plot_scores.append(reward)
        #     total_score += reward
        #     mean_score = total_score / agent.n_games
        #     plot_mean_scores.append(mean_score)
        #     # plot(plot_scores, plot_mean_scores)


if __name__ == '__main__':
    train()