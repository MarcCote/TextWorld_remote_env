"""
Module that contains the command line app.

Why does this file exist, and why not put this in __main__?

  You might be tempted to import things from __main__ later, but that will cause
  problems: the code will get executed twice:

  - When you run `python -mtextworld_remote_env` python will execute
    ``__main__.py`` as a script. That means there won't be any
    ``textworld_remote_env.__main__`` in ``sys.modules``.
  - When you import __main__ it will get executed again (as a module) because
    there's no ``textworld_remote_env.__main__`` in ``sys.modules``.

  Also see (1) from http://click.pocoo.org/5/setuptools/#setuptools-integration
"""
import click
import redis

from textworld_remote_env import messages
from textworld_remote_env import state
from textworld_remote_env.message_broker import ServiceMessageBroker

import json
import numpy as np
import os
import timeout_decorator
import time

import textworld
import crowdai_api
import random

import glob

########################################################
# CONSTANTS
########################################################
PER_STEP_TIMEOUT = 10*60 # 10minutes


class TextWorldRemoteEnvEvaluatorService:
    def __init__(   self,
                    game_paths = [],
                    max_steps = 1000,
                    verbose = False):
        self.game_paths = game_paths
        self.max_steps = max_steps

        self.message_broker = ServiceMessageBroker()

        self.current_game = -1
        self.current_game_begin_time = False
        self.current_env = False
        self.evaluation_state = {}
        self.init_evaluation_state()

    def init_evaluation_state(self):
        absolute_game_paths = []
        for _game_path in self.game_paths:
            assert os.path.exists(_game_path), \
                "GamePath : {} does not exist !".format(_game_path)
            absolute_game_paths.append(
                os.path.abspath(_game_path)
            )
        random.shuffle(absolute_game_paths)
        self.game_paths = absolute_game_paths

        self.evaluation_state["state"] = state.EvaluationState.EVALUATION_PENDING
        self.evaluation_state["episodes"] = []
        for _game_path in self.game_paths:
            _episode_object = {}
            _episode_object["state"] = state.EpisodeState.EPISODE_PENDING
            _episode_object["game"] = os.path.basename(_game_path)
            _episode_object["steps"] = 0
            _episode_object["reward"] = 0
            _episode_object["time"] = 0
            _episode_object["begin_time"] = False
            self.evaluation_state["episodes"].append(
                _episode_object
            )
        
        # Sync Evaluation State with the Oracle
        self.message_broker.sync_info_event_with_oracle(
                self.evaluation_state,
                force=True)

    def get_current_episode_oject(self):
        return self.evaluation_state["episodes"][self.current_game]

    def handle_get_game_file(self):
        self.current_game += 1

        """
        First ensure that if any of the previous episodes are pending 
        (meaning, that the agent  abandoned them before they were "done")
        then we mark them as Abandoned
        """
        for _game_idx in range(self.current_game):
            _episode_object = self.evaluation_state["episodes"][_game_idx]
            if _episode_object["state"] != state.EpisodeState.EPISODE_SUCCESSFUL:
                """
                    TODO: Check with TextWorld team what the best policy 
                    should be here.
                """
                #raise Exception('Agent Abandoned an episode before it was "done"')
                _episode_object["state"] = state.EpisodeState.EPISODE_ABANDONED

        if self.current_game >= len(self.game_paths):
            """
                Do due dilligence to mark the end of the evaluation
            """
            self.evaluation_state["state"] = \
                state.EvaluationState.EVALUATION_SUCCESSFUL

            mean_reward = np.mean(
                [
                    _episode["reward"]
                    for _episode in self.evaluation_state["episodes"]
                ]
            )
            mean_time = np.mean(
                [
                    _episode["time"]
                    for _episode in self.evaluation_state["episodes"]
                ]
            )

            self.evaluation_state["score"] = {
                "score" : mean_reward,
                "score_secondary" : mean_time
            }

            print(  "Successful  evaluation state : ", 
                    json.dumps(self.evaluation_state, indent=4))

            # Sync Evaluation State with the Oracle
            self.message_broker.sync_success_event_with_oracle(
                    self.evaluation_state,
                    force=True)

            """
                Return False
            """
            self.message_broker.send_game_file(False)
        else:
            """
                instantiate a new env with the available game_path
                and return the game_path to the client
                (assuming the same game_path is available to the client too)
            """
            if self.current_env:
                self.current_env.close()

            game_file_path = self.game_paths[self.current_game]
            self.current_env = textworld.start(game_file_path)
            self.message_broker.send_game_file(game_file_path)
            self.evaluation_state["state"] = \
                state.EvaluationState.EVALUATION_RUNNING
            _episode_object = self.get_current_episode_oject()
            _episode_object["begin_time"] = time.time()

            # Sync Evaluation State with the Oracle
            self.message_broker.sync_info_event_with_oracle(
                    self.evaluation_state,
                    force=True)


    def handle_activate_state_tracking(self):
        self.current_env.activate_state_tracking()
        self.message_broker.acknowledge_command()

    def handle_compute_intermediate_reward(self):
        self.current_env.compute_intermediate_reward()
        self.message_broker.acknowledge_command()

    def handle_step(self, _event):
        command = _event["payload"]["command"]
        game_state, reward, done = self.current_env.step(command)

        _episode_object = self.get_current_episode_oject()
        _episode_object["steps"] = game_state.nb_moves
        _episode_object["reward"] = game_state.score
        _episode_object["time"] = time.time() - _episode_object["begin_time"]

        if done:
            _episode_object["state"] = state.EpisodeState.EPISODE_SUCCESSFUL

        # Sync Evaluation State with the Oracle
        self.message_broker.sync_info_event_with_oracle(
                self.evaluation_state,
                force=False)

        self.message_broker.acknowledge_command()


    def handle_reset(self):
        if self.current_env.game_running:
            """
                In the evaluation mode, the agent is allowed to call reset 
                only once on a newly instantiated environment
            """
            raise Exception("Attempt to call env.reset on an already running environment.")

        _episode_object = self.get_current_episode_oject()
        _episode_object["state"] = state.EpisodeState.EPISODE_RUNNING

        # Sync Evaluation State with the Oracle
        self.message_broker.sync_info_event_with_oracle(
                self.evaluation_state,
                force=False)

        self.current_env.reset()
        self.message_broker.acknowledge_command()

    def handle_close(self):
        self.current_env.close()
        self.message_broker.acknowledge_command()

    @timeout_decorator.timeout(10*60) #Time out of 10 minutess
    def get_next_command(self):
        """
            Try to get next command from the agent.
            If the agent doesnt respond within 10 minutes, then throw a timeout
        """
        return next(self.message_broker.remote_handler)

    def run_wrapper(self):
        print("Listening for Agent....")
        while True:
            try:
                _event = self.get_next_command()
            except timeout_decorator.timeout_decorator.TimeoutError:
                raise Exception("Vanishing Agent : Agent hasnt communicated with the evaluator for 10minutes. Abadoning evaluation.")

            print(_event)
            if _event["event_type"] == state.Commands.GET_GAME_FILE:
                self.handle_get_game_file()
            elif _event["event_type"] == state.Commands.ACTIVATE_STATE_TRACKING:
                self.handle_activate_state_tracking()
            elif _event["event_type"] == state.Commands.COMPUTE_INTERMEDIATE_REWARD:
                self.handle_compute_intermediate_reward()
            elif _event["event_type"] == state.Commands.STEP:
                self.handle_step(_event)
            elif _event["event_type"] == state.Commands.RESET:
                self.handle_reset()
            elif _event["event_type"] == state.Commands.CLOSE:
                self.handle_close()

        # Sync Evaluation State with the Oracle
        self.message_broker.sync_info_event_with_oracle(
                self.evaluation_state,
                force=True)


    def run(self):
        try:
            self.run_wrapper()
        except Exception as e:
            self.evaluation_state["state"] = state.EvaluationState.EVALUATION_ERROR
            self.evaluation_state["error"] = str(e)
            if self.current_game >= 0:
                self.evaluation_state["episodes"][self.current_game]["state"] = state.EpisodeState.EPISODE_ERROR

            print(  "Current evaluation state : ",
                    json.dumps(self.evaluation_state, indent=4))
            # Sync Evaluation State with the Oracle
            self.message_broker.sync_error_event_with_oracle(
                    self.evaluation_state,
                    force=True)

@click.command()
@click.option('--game_paths_folder', required=True)
def main(game_paths_folder):
    game_paths = glob.glob(
                    os.path.join(game_paths_folder,"*.ulx")
                    )
    print("Game Paths : ", game_paths)
    service = TextWorldRemoteEnvEvaluatorService(
        game_paths = game_paths
    )
    service.run()
