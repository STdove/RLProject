import gym
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from matplotlib import pyplot as plt
from torch.distributions import Categorical
from Tree_env_1 import TreeEnv

MAX_EPISODE_LENGTH = 1000
DISCOUNT_FACTOR = 1.0
SEED = 0
MIN_BATCH_SIZE = 256

env = TreeEnv()

loss = 0  # global loss var


class Policy(nn.Module):
    """Define policy network"""

    def __init__(self, observation_space, action_space, hidden_size=128):
        super(Policy, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(env.observation_space.n, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, action_space.n),
            nn.Softmax(dim=0)
        )

    def forward(self, x):
        output = self.net(x)
        return output


policy = Policy(env.observation_space, env.action_space)
optimizer = optim.Adam(policy.parameters(), lr=1e-5)


def compute_returns(rewards, discount_factor=DISCOUNT_FACTOR):
    """Compute discounted returns"""
    returns = []
    for i in range(len(rewards)):
        G = np.sum([reward * discount_factor ** j for j, reward in enumerate(rewards[i:])])
        returns.append(G)  # all returns correspond to each time step
    return returns


def policy_improvement(log_probs, rewards):
    """Compute REINFORCE policy gradient and perform gradient ascent step"""
    returns = compute_returns(rewards)

    returns = torch.tensor(returns)
    returns = (returns - returns.mean()) / (returns.std())  # normalized return
    global loss
    loss = 0
    for log_prob, ret in zip(log_probs, returns):
        loss -= log_prob * ret  # without baseline
    return float(loss.data)  # this only return scalar value, not tensor


def act(state):
    """ Use policy to sample an action and return probability for gradient update"""
    state = torch.tensor(state)
    state = state.float()
    prob_dist = policy(state)  # probability distribution of actions given state
    actions = [i for i in range(env.action_space.n)]  # all possible actions
    action = np.random.choice(actions,
                              p=prob_dist.clone().detach().numpy())  # sample an action in terms of probability distribution
    return action, torch.log(prob_dist[action])


def policy_gradient(num_episodes):
    rewards = []
    for episode in range(num_episodes):
        rewards.append(0)
        trajectory = []
        state = env.reset()
        # state_flatten = state.flatten('F')

        for t in range(MAX_EPISODE_LENGTH):
            #             if episode % (num_episodes / 100) == 0:
            #                 env.render()

            action, log_prob = act(state)

            # next_state, reward, done, _ = env.step(action.item())
            next_state, reward, done, _, = env.step(action)
            # next_state_flatten = next_state.flatten('F')

            trajectory.append((log_prob, reward))

            # state_flatten = next_state
            state = next_state
            rewards[-1] += reward

            if done:
                break

        policy_improvement(*zip(*trajectory))
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()  # backpropagation and gradient ascent

        if episode % (num_episodes / 100) == 0:
            print("Mean Reward: ", np.mean(rewards[-int(num_episodes / 100):]))
    return rewards

def evaluation(env, fix_seed=True, seed=0):
    state = env.reset(fix_seed, seed)

    current_total_reward = 0
    for _ in range(1000):
        # env.render(current_total_reward)
        action, log_prob = act(state)
        next_state, get_reward, done, _, = env.step(action)
        state = next_state
        current_total_reward += get_reward
        if done:
            print(f"with action from q_learning get reward {current_total_reward}")
            break
        print(f'state: {state}, action: {action}')

        # time.sleep(2)
    return current_total_reward

if __name__ == "__main__":
    rewards = policy_gradient(10000)

    # save model
    torch.save(policy.state_dict(), 'policy_gradient_model')

    _, ax = plt.subplots()
    ax.step([i for i in range(1, len(rewards) + 1)], rewards, linewidth=1.0)
    ax.grid()
    ax.set_xlabel('episode')
    ax.set_ylabel('reward')
    plt.title('Version 1 & Policy Gradient')
    plt.show()

    print(f'Mean reward: {np.mean(rewards)}')
    print(f'Standard deviation: {np.std(rewards)}')
    print(f'Max reward: {np.max(rewards)}')
    print(f'Min reward: {np.min(rewards)}')

    # read model
    policy = Policy(env.observation_space, env.action_space)
    policy.load_state_dict(torch.load('policy_gradient_model'))

    # evaluation
    eval_rewards = []
    for seed in range(0, 50):
        r = evaluation(env, False, seed)
        eval_rewards.append(r)

    # random simulation
    sim_rewards = []
    for seed in range(0, 50):
        obs = env.reset(False, seed)
        current_total_reward = 0
        for _ in range(1000):
            obs, reward, done, _ = env.step(np.random.randint(0, 8))
            current_total_reward += reward
            if done:
                break
        sim_rewards.append(reward)
    plt.figure()
    plt.subplot()
    plt.bar([i for i in range(len(eval_rewards))], eval_rewards)
    plt.subplot()
    plt.bar([i for i in range(len(eval_rewards))], sim_rewards)
    plt.xlabel('seed')
    plt.ylabel('reward')
    plt.show()

    env.close()
