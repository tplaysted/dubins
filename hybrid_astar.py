from math import pi, tan, sqrt
import matplotlib.pyplot as plt
from matplotlib.collections import PatchCollection, LineCollection
from matplotlib.patches import Rectangle
import matplotlib.animation as animation
import numpy as np
import argparse

from grid import Grid
from car import SimpleCar
from environment import Environment
from dubins_path import DubinsPath
from astar import Astar
from test_cases.cases import TestCase
from utils.utils import plot_a_car, get_discretized_thetas, round_theta

from time import time


class Node:
    """ Hybrid A* tree node. """

    def __init__(self, grid_pos, pos):

        self.grid_pos = grid_pos
        self.pos = pos
        self.g = None
        self.g_ = None
        self.f = None
        self.parent = None
        self.phi = 0
        self.branches = []

    def __eq__(self, other):

        return self.grid_pos == other.grid_pos
    
    def __hash__(self):

        return hash((self.grid_pos))


class HybridAstar:
    """ Hybrid A* search procedure. """

    def __init__(self, car, grid, unit_theta=pi/12, dt=1e-2, check_dubins=1):
        
        self.car = car
        self.grid = grid
        self.unit_theta = unit_theta
        self.dt = dt
        self.check_dubins = check_dubins

        self.start = self.car.start_pos
        self.goal = self.car.end_pos

        self.r = self.car.l / tan(self.car.max_phi)
        self.drive_steps = int(sqrt(2)*self.grid.cell_size/self.dt) + 1
        self.arc = self.drive_steps * self.dt
        self.phil = [-self.car.max_phi, 0, self.car.max_phi]

        self.dubins = DubinsPath(self.car)
        self.astar = Astar(self.grid, self.goal[:2])
        
        self.w1 = 0.95 # weight for astar heuristic
        self.w2 = 0.05 # weight for simple heuristic
        self.w3 = 0.40 # weight for extra cost of steering angle change
        self.w4 = 0.20 # weight for extra cost of turning

        self.thetas = get_discretized_thetas(self.unit_theta)
    
    def construct_node(self, pos):
        """ Create node for a pos. """

        theta = pos[2]
        pt = pos[:2]

        theta = round_theta(theta % (2*pi), self.thetas)
        
        cell_id = self.grid.to_cell_id(pt)
        grid_pos = cell_id + [theta]

        node = Node(grid_pos, pos)

        return node
    
    def simple_heuristic(self, pos):
        """ Heuristic by Manhattan distance. """

        return abs(self.goal[0]-pos[0]) + abs(self.goal[1]-pos[1])
        
    def astar_heuristic(self, pos):
        """ Heuristic by standard astar. """

        h1 = self.astar.search_path(pos[:2]) * self.grid.cell_size
        h2 = self.simple_heuristic(pos[:2])
        
        return self.w1*h1 + self.w2*h2

    def get_children(self, node, heu, extra):
        """ Get successors from a state. """

        children = []
        for phi in self.phil:

            pos = node.pos
            branch = [pos[:2]]

            for _ in range(self.drive_steps):
                pos = self.car.step(pos, phi)
                branch.append(pos[:2])

            # check safety of route-----------------------
            if phi == 0:
                safe = self.dubins.is_straight_route_safe(node.pos, pos)
            else:
                d, c, r = self.car.get_params(node.pos, phi)
                safe = self.dubins.is_turning_route_safe(node.pos, pos, d, c, r)
            # --------------------------------------------
            
            if not safe:
                continue
            
            child = self.construct_node(pos)
            child.phi = phi
            child.parent = node
            child.g = node.g + self.arc
            child.g_ = node.g_ + self.arc

            if extra:
                # extra cost for changing steering angle
                if phi != node.phi:
                    child.g += self.w3 * self.arc
                
                # extra cost for turning
                if phi != 0:
                    child.g += self.w4 * self.arc

            if heu == 0:
                child.f = child.g + self.simple_heuristic(child.pos)
            if heu == 1:
                child.f = child.g + self.astar_heuristic(child.pos)
            
            children.append(child)
            node.branches.append(branch)

        return children
    
    def best_final_shot(self, open_, closed_, best, cost, d_route, n=10):
        """ Search best final shot in open set. """

        open_.sort(key=lambda x: x.f, reverse=False)

        for t in range(min(n, len(open_))):
            best_ = open_[t]
            solutions_ = self.dubins.find_tangents(best_.pos, self.goal)
            d_route_, cost_, valid_ = self.dubins.best_tangent(solutions_)
        
            if valid_ and cost_ + best_.g_ < cost + best.g_:
                best = best_
                cost = cost_
                d_route = d_route_
        
        if best in open_:
            open_.remove(best)
            closed_.append(best)
        
        return best, cost, d_route
    
    def backtracking(self, node):
        """ Backtracking the path. """

        route = []
        while node.parent:
            route.append((node.pos, node.phi))
            node = node.parent
        
        return list(reversed(route))
    
    def search_path(self, heu=1, extra=False):
        """ Hybrid A* pathfinding. """

        root = self.construct_node(self.start)
        root.g = float(0)
        root.g_ = float(0)
        
        if heu == 0:
            root.f = root.g + self.simple_heuristic(root.pos)
        if heu == 1:
            root.f = root.g + self.astar_heuristic(root.pos)

        closed_ = []
        open_ = [root]

        count = 0
        while open_:
            count += 1
            best = min(open_, key=lambda x: x.f)

            open_.remove(best)
            closed_.append(best)

            # check dubins path
            if count % self.check_dubins == 0:
                solutions = self.dubins.find_tangents(best.pos, self.goal)
                d_route, cost, valid = self.dubins.best_tangent(solutions)
                
                if valid:
                    best, cost, d_route = self.best_final_shot(open_, closed_, best, cost, d_route)
                    route = self.backtracking(best) + d_route
                    path = self.car.get_path(self.start, route)
                    cost += best.g_
                    print('Shortest path: {}'.format(round(cost, 2)))
                    print('Total iteration:', count)
                    
                    return path, closed_

            children = self.get_children(best, heu, extra)

            for child in children:

                if child in closed_:
                    continue

                if child not in open_:
                    open_.append(child)

                elif child.g < open_[open_.index(child)].g:
                    open_.remove(child)
                    open_.append(child)

        return None, None


def main(heu=1, extra=False, grid_on=False):

    tc = TestCase()

    env = Environment(tc.obs)

    car = SimpleCar(env, tc.start_pos, tc.end_pos, max_phi=pi/5)

    grid = Grid(env)
    
    hastar = HybridAstar(car, grid)

    t = time()
    path, closed_ = hastar.search_path(heu, extra)
    print('Total time: {}s'.format(round(time()-t, 3)))

    if not path:
        print('No valid path!')
        return
    
    branches = []
    bnodex, bnodey = [], []
    for node in closed_:
        branches += node.branches
        for _ in range(len(node.branches)):
            bnodex.append(node.pos[0])
            bnodey.append(node.pos[1])

    xl, yl = [], []
    carl = []
    for i in range(len(path)):
        xl.append(path[i].pos[0])
        yl.append(path[i].pos[1])
        carl.append(path[i].model[0])

    end_state = car.get_car_state(car.end_pos)

    # plot and annimation
    fig, ax = plt.subplots(figsize=(6,6))
    ax.set_xlim(0, env.lx)
    ax.set_ylim(0, env.ly)
    ax.set_aspect("equal")

    if grid_on:
        ax.set_xticks(np.arange(0, env.lx, grid.cell_size))
        ax.set_yticks(np.arange(0, env.ly, grid.cell_size))
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        ax.tick_params(length=0)
        plt.grid(which='both')
    else:
        ax.set_xticks([])
        ax.set_yticks([])
    
    for ob in env.obs:
        ax.add_patch(Rectangle((ob.x, ob.y), ob.w, ob.h, fc='gray', ec='k'))
    
    ax.plot(car.start_pos[0], car.start_pos[1], 'ro', markersize=5)
    ax = plot_a_car(ax, end_state.model)

    _branches = LineCollection([], color='b', alpha=0.8, linewidth=1)
    ax.add_collection(_branches)
    _nodes, = ax.plot([], [], 'ro', markersize=3)

    _path, = ax.plot([], [], color='lime', linewidth=2)
    _carl = PatchCollection([])
    ax.add_collection(_carl)
    _path1, = ax.plot([], [], color='whitesmoke', linewidth=2)
    _car = PatchCollection([])
    ax.add_collection(_car)
    
    frames = len(branches) + len(path) + 1

    def init():
        _branches.set_paths([])
        _nodes.set_data([], [])
        _path.set_data([], [])
        _carl.set_paths([])
        _path1.set_data([], [])
        _car.set_paths([])

        return _branches, _nodes, _path, _carl, _path1, _car

    def animate(i):

        if i < len(branches):
            _branches.set_paths(branches[:i+1])
            _nodes.set_data(bnodex[:i+1], bnodey[:i+1])
        
        else:
            _branches.set_paths(branches)
            _nodes.set_data(bnodex, bnodey)

            j = i - len(branches)

            _path.set_data(xl[min(j, len(path)-1):], yl[min(j, len(path)-1):])

            sub_carl = carl[:min(j+1, len(path))]
            _carl.set_paths(sub_carl[::20])
            _carl.set_color('m')
            _carl.set_alpha(0.1)
            _carl.set_zorder(3)

            _path1.set_data(xl[:min(j+1, len(path))], yl[:min(j+1, len(path))])
            _path1.set_zorder(3)

            edgecolor = ['k']*5 + ['r']
            facecolor = ['y'] + ['k']*4 + ['r']
            _car.set_paths(path[min(j, len(path)-1)].model)
            _car.set_edgecolor(edgecolor)
            _car.set_facecolor(facecolor)
            _car.set_zorder(3)

        return _branches, _nodes, _path, _carl, _path1, _car

    ani = animation.FuncAnimation(fig, animate, init_func=init, frames=frames,
                                  interval=1, repeat=False, blit=True)

    plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--heu', type=int, default=1, help='heuristic type')
    parser.add_argument('--extra', type=bool, default=False, help='add extra cost or not')
    parser.add_argument('--grid_on', type=bool, default=False, help='show grid or not')
    opt = parser.parse_args()

    main(**vars(opt))
