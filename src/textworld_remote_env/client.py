# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT license.


# -*- coding: utf-8 -*-
import os
import re
import sys
import textwrap
import subprocess
from pkg_resources import Requirement, resource_filename

from typing import Mapping, Union, Tuple, List

import numpy as np

from glk import ffi, lib
from io import StringIO

import textworld
from textworld.generator.game import Game, GameProgression
from textworld.logic import Action, State
from textworld.core import GameNotRunningError

from textworld_remote_env.message_broker import ClientMessageBroker

GLULX_PATH = resource_filename(
                Requirement.parse('textworld'), 
                'textworld/thirdparty/glulx/Git-Glulx'
                )

from textworld.envs.glulx.git_glulx_ml import MissingGameInfosError, \
                    StateTrackingIsRequiredError, OraclePolicyIsRequiredError, \
                    _strip_input_prompt_symbol, _strip_i7_event_debug_tags, \
                    _detect_i7_events_debug_tags, GlulxGameState

class RemoteEnv():
    def __init__(self) -> None:
        self.message_broker = ClientMessageBroker()
    def start(self):
        gamefile = self.message_broker.get_game_file()
        if gamefile == False:
            return False
        else:
            return GlulxEnvironmentWrapper(gamefile)

class GlulxEnvironmentWrapper(textworld.Environment):
    """ 
    
    """
    metadata = {'render.modes': ['human', 'ansi', 'text']}

    def __init__(self, gamefile) -> None:
        """ Creates a GitGlulxML from the given gamefile
        """
        super().__init__()

        self.message_broker = ClientMessageBroker()
        
        self._gamefile = gamefile
        self._process = None

        # Load initial state of the game.
        filename, ext = os.path.splitext(gamefile)
        game_json = filename + ".json"

        if not os.path.isfile(game_json):
            raise MissingGameInfosError()

        self._state_tracking = False
        self._compute_intermediate_reward = False
        self.game = Game.load(game_json)
        self.game_state = None

    def activate_state_tracking(self) -> None:
        self.message_broker.activate_state_tracking()
        self._state_tracking = True

    def compute_intermediate_reward(self) -> None:
        self.message_broker.compute_intermediate_reward()
        self._compute_intermediate_reward = True

    def __del__(self) -> None:
        self.close()

    @property
    def game_running(self) -> bool:
        """ Determines if the game is still running. """
        return self._process is not None and self._process.poll() is None

    def step(self, command: str) -> Tuple[GlulxGameState, float, bool]:
        self.message_broker.step(command)
        if not self.game_running:
            raise GameNotRunningError()

        command = command.strip()
        output = self._send(command)
        if output is None:
            raise GameNotRunningError()

        self.game_state = self.game_state.update(command, output)
        self.game_state.has_timeout = not self.game_running
        return self.game_state, self.game_state.score, self.game_state.game_ended

    def _send(self, command: str) -> Union[str, None]:
        if not self.game_running:
            return None

        if len(command) == 0:
            command = " "

        c_command = ffi.new('char[]', command.encode('utf-8'))
        result = lib.communicate(self._names_struct, c_command)
        if result == ffi.NULL:
            self.close()
            return None

        result = ffi.gc(result, lib.free)
        return ffi.string(result).decode('utf-8')

    def reset(self) -> GlulxGameState:
        self.message_broker.reset()
        if self.game_running:
            self.close()

        self._names_struct = ffi.new('struct sock_names*')

        lib.init_glulx(self._names_struct)
        sock_name = ffi.string(self._names_struct.sock_name).decode('utf-8')
        self._process = subprocess.Popen(["%s/git-glulx-ml" % (GLULX_PATH,), self._gamefile, '-g', sock_name, '-q'])
        c_feedback = lib.get_output_nosend(self._names_struct)
        if c_feedback == ffi.NULL:
            self.close()
            raise ValueError("Game failed to start properly: {}.".format(self._gamefile))
        c_feedback = ffi.gc(c_feedback, lib.free)

        start_output = ffi.string(c_feedback).decode('utf-8')

        self.game_state = GlulxGameState(self)
        self.game_state.init(start_output, self.game, self._state_tracking, self._compute_intermediate_reward)

        # TODO: check if the game was compiled in debug mode. You could parse
        #       the output of the following command to check whether debug mode
        #       was used or not (i.e. invalid action not found).
        self._send('actions')  # Turn on debug print for Inform7 action events.
        self._send('restrict commands')  # Restrict Inform7 commands.

        return self.game_state

    def close(self) -> None:
        self.message_broker.close()
        if self.game_running:
            self._process.kill()
            self._process = None

        try:
            lib.cleanup_glulx(self._names_struct)
        except AttributeError:
            pass  # Attempted to kill before reset

    def render(self, mode: str = "human") -> None:
        outfile = StringIO() if mode in ['ansi', "text"] else sys.stdout

        msg = self.game_state.feedback.rstrip() + "\n"
        if self.display_command_during_render and self.game_state.command is not None:
            msg = '> ' + self.game_state.command + "\n" + msg

        # Wrap each paragraph.
        if mode == "human":
            paragraphs = msg.split("\n")
            paragraphs = ["\n".join(textwrap.wrap(paragraph, width=80)) for paragraph in paragraphs]
            msg = "\n".join(paragraphs)

        outfile.write(msg + "\n")

        if mode == "text":
            outfile.seek(0)
            return outfile.read()

        if mode == 'ansi':
            return outfile
