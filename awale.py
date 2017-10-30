import random
import copy
import time
import threading
import Tkinter as tk
import sys
import math


class Awale:
    def __init__(self, player1, player2):
        self.state = Awale.initial_state()

        self.players = (player1, player2)
        player1.set_id(0)
        player2.set_id(1)

        self.gui = AwaleGui(self)

    @staticmethod
    def initial_state():
        return {
            "board": [[4 for hole in xrange(6)] for side in xrange(2)],
            "score": [0, 0],
            "turn": int(random.getrandbits(1))}

    @staticmethod
    def possible_actions(state):
        this_side = state["board"][state["turn"]]
        that_side = state["board"][1 - state["turn"]]
        actions = [i + 1 for i, s in enumerate(this_side) if s > 0]
        if max(that_side) == 0:
            actions = [a for a in actions if that_side[a - 1] > 6 - a]
        return actions

    @staticmethod
    def is_terminal(state):
        return len(Awale.possible_actions(state)) == 0

    @staticmethod
    def next_state(state, action):
        state = copy.deepcopy(state)

        def next_hole(side, hole):
            if side == 0:
                if hole > 0:
                    return 0, hole - 1
                return 1, 0
            if hole < 5:
                return 1, hole + 1
            return 0, 5

        def prev_hole(side, hole):
            if side == 0:
                if hole < 5:
                    return 0, hole + 1
                return 1, 5
            if hole > 0:
                return 1, hole - 1
            return 0, 0

        board = state["board"]
        turn = state["turn"]
        score = state["score"]
        side = turn
        hole = action - 1

        seeds = board[side][hole]
        board[side][hole] = 0

        while seeds > 0:
            side, hole = next_hole(side, hole)
            if side == turn and hole == action - 1:
                continue
            seeds -= 1
            state["board"][side][hole] += 1

        while side != turn and board[side][hole] in [2, 3]:
            score[turn] += board[side][hole]
            board[side][hole] = 0
            side, hole = prev_hole(side, hole)

        state["turn"] = 1 - turn
        return state

    def move(self, action):
        possible_actions = self.possible_actions(self.state)
        if action not in possible_actions:
            print "Invalid action: chose a hole in", possible_actions
            return False
        self.state = self.next_state(self.state, action)
        self.gui.update(self.state)
        return True

    def print_board(self):
        print ""

        print "Score: %d" % self.state["score"][0]
        for side in self.state["board"]:
            print side
        print "Score: %d" % self.state["score"][1]

        print ""

    def print_result(self):
        winner = int(self.state["score"][1] > self.state["score"][0])
        print "And the winner is... %s (%d x %d)" % (self.players[winner].name, self.state["score"][0], self.state["score"][1])

    def start(self, first=None):
        player1, player2 = self.players

        if first is None:
            first = int(random.getrandbits(1))
        self.state["turn"] = first

        player1.start(self.state)
        player2.start(self.state)

        print ""
        while not self.is_terminal(self.state):
            player = self.players[self.state["turn"]]

            print player.name + " to play:",
            sys.stdout.flush()

            player.think()
            while player.is_thinking():
                player1.think(.5)
                player2.think(.5)

            action = player.guess()

            if self.move(action):
                player1.move(action)
                player2.move(action)
        print self.possible_actions(self.state)


class AwaleGui(threading.Thread):
    alive = True
    action = []

    def __init__(self, match):
        self.match = match
        threading.Thread.__init__(self)
        self.start()

    def callback(self):
        self.root.destroy()
        AwaleGui.alive = False

    def run(self):
        self.root = tk.Tk()
        self.root.wm_title("Awale")
        self.root.protocol("WM_DELETE_WINDOW", self.callback)

        def click(player, hole):
            def action():
                if player.id == self.match.state["turn"]:
                    AwaleGui.action.append(hole)
                    print hole
            return action

        self.scores = [tk.Label(self.root), tk.Label(self.root)]
        self.scores[0].grid(row=0, columnspan=6)
        self.scores[1].grid(row=3, columnspan=6)
        self.scores[0].config(height=5)
        self.scores[1].config(height=5)

        self.buttons = [[], []]
        for side in xrange(2):
            for hole in xrange(6):
                self.buttons[side].append(tk.Button(self.root))
                self.buttons[side][hole].config(
                    height=5, width=7, wraplength=30)
                self.buttons[side][hole].grid(row=1 + side, column=hole)

                player = self.match.players[side]
                if player.is_human():
                    self.buttons[side][hole].config(
                        command=click(player, hole + 1))

        self.update(self.match.state)

        self.root.mainloop()

    def update(self, state):
        for i in xrange(2):
            self.scores[i].config(text="%s score: %d" % (
                self.match.players[i].name, state["score"][i]))

        for side in xrange(2):
            for hole in xrange(6):
                value = state["board"][side][hole]
                self.buttons[side][hole].config(text='o' * value)


class TreeSearch:
    class Node:
        def __init__(self, state, parent=None):
            self.state = state
            self.parent = parent
            self.children = {}
            self.visits = 0
            self.victories = 0

        def uct(self):
            wi = float(self.victories)
            ni = float(self.visits) + 1.
            t = float(self.parent.visits) + 1.
            C = 1.
            u = wi / ni + C * math.sqrt(math.log(t) / ni)
            return u

    def __init__(self, game):
        self.game = game
        self.root = None
        self.player = None
        self.time_to_think = 1.

    def start(self, state):
        self.root = self.Node(copy.deepcopy(state), None)

    def weighted_choice(self, options, weights):
        weights_sum = sum(weights)
        weights = [w / weights_sum for w in weights]

        x = random.random()
        for option, weight in zip(options, weights):
            if x < weight:
                return option
            x -= weight

    def selection(self, node):
        while len(node.children) > 0:
            children, weights = zip(*[(c, c.uct())
                                      for c in node.children.values()])
            node = self.weighted_choice(children, weights)
        return node

    def expansion(self, node):
        game = self.game

        if game.is_terminal(node.state):
            return node

        state = node.state
        for action in game.possible_actions(state):
            node.children[action] = self.Node(
                game.next_state(state, action), node)

        child = random.choice(node.children.values())

        return child

    def simulation(self, node):
        game = self.game
        state = node.state

        while not game.is_terminal(state):
            action = random.choice(game.possible_actions(state))
            state = game.next_state(state, action)

        result = int(state["score"][self.player] >
                     state["score"][1 - self.player])
        #result = state["score"][self.player] - state["score"][1 - self.player]
        return result

    def backprop(self, node, result):
        while True:
            node.visits += 1
            node.victories += result

            node = node.parent
            if node is None:
                break

    def explore(self):
        node = self.root
        node = self.selection(node)
        node = self.expansion(node)
        result = self.simulation(node)
        self.backprop(node, result)

    def think(self, time_to_think=None):
        if time_to_think is None:
            time_to_think = self.time_to_think

        start = time.time()
        while time.time() - start < time_to_think:
            self.explore()

    def guess(self):
        node = self.root

        best_score = None
        for action, child in node.children.items():
            score = child.victories * 1. / (child.visits + 1)
            if score > best_score:
                best_score = score
                best_action = action
            # print "%d: %.3f," % (action, score),
        print "%d (%d paths considered)" % (best_action, node.visits)

        return best_action

    def move(self, action):
        self.root = self.root.children[action]


class Player:
    def __init__(self, name, ai=None):
        self.id = None
        self.name = name
        self.ai = ai

        self.action = None

        if not self.is_human():
            self.set_time_to_think()

    def set_time_to_think(self):
        print "\nHow long can %s think for (seconds)?" % (self.name)
        while True:
            try:
                self.ai.time_to_think = float(input("> "))
                return
            except:
                print "Invalid answer... how long?"

    def is_human(self):
        return self.ai is None

    def think(self, t=None):
        self.action = None
        if not self.is_human():
            self.ai.think(t)
            if t is None:
                self.action = self.ai.guess()

    def is_thinking(self):
        if not AwaleGui.alive:
            exit()
        if self.is_human() and len(AwaleGui.action) > 0:
            self.action = AwaleGui.action.pop()
        return self.action is None

    def guess(self):
        return self.action

    def move(self, action):
        if not self.is_human():
            self.ai.move(action)

    def start(self, state):
        if not self.is_human():
            self.ai.start(state)
            self.think(1.)

    def set_id(self, player):
        self.id = player
        if not self.is_human():
            self.ai.player = player


def _main():
    # Who plays
    print "Who's playing?"
    options = {
        1: "Two people",
        2: "You vs AI",
        3: "AI vs AI"}
    for key, value in options.items():
        print " %s\t%s" % (key, value)

    who_plays = None
    while who_plays not in options.keys():
        who_plays = input("> ")
        if who_plays == 1:
            player1 = Player("Player 1")
            player2 = Player("Player 2")
        elif who_plays == 2:
            player1 = Player("Computer", ai=TreeSearch(Awale))
            player2 = Player("You")
        elif who_plays == 3:
            player1 = Player("Computer 1", ai=TreeSearch(Awale))
            player2 = Player("Computer 2", ai=TreeSearch(Awale))
        else:
            print("Invalid answer... who's playing?")

    # Who begins
    print "\nWho begins?"
    options = {
        1: player1.name,
        2: player2.name}
    for key, value in options.items():
        print " %s\t%s" % (key, value)

    who_begins = input("> ")
    while who_begins not in options.keys():
        print("Invalid answer... who begins?")
        who_begins = input("> ")
    who_begins -= 1

    match = Awale(player1, player2)
    match.start(who_begins)
    match.print_result()


if __name__ == "__main__":
    _main()
