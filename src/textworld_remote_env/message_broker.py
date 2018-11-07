#!usr/bin/env python

import crowdai_api
from textworld_remote_env import state

class ClientMessageBroker:
    def __init__(self):
        self.remote_handler = crowdai_api.events.CrowdAIEvents()
    
    def get_blocking_call_response(self, event_type, payload={}):
        response = self.remote_handler.register_event(
            event_type=event_type,
            payload=payload,
            blocking=True
        )
        if response == None:
            raise Exception("Did you set the CROWDAI_IS_GRADING env variable as True ?")
        return response

    def get_game_file(self):
        response = self.get_blocking_call_response(state.Commands.GET_GAME_FILE)
        game_file = response["game_file"]
        print("Received game_file")
        return game_file
    
    def activate_state_tracking(self):
        response = self.get_blocking_call_response(state.Commands.ACTIVATE_STATE_TRACKING)
        assert response["ack"] == True, "Server did not acknowledge a command"
    
    def compute_intermediate_reward(self):
        response = self.get_blocking_call_response(state.Commands.ACTIVATE_STATE_TRACKING)
        assert response["ack"] == True, "Server did not acknowledge a command"
    
    def step(self, command):
        response = self.get_blocking_call_response(
                    state.Commands.STEP,
                    payload={"command" : command}
                    )
        print(response)
        assert response["ack"] == True, "Server did not acknowledge a command"
    
    def reset(self):
        response = self.get_blocking_call_response(state.Commands.RESET)
        assert response["ack"] == True, "Server did not acknowledge a command"

    def close(self):
        response = self.get_blocking_call_response(state.Commands.CLOSE)
        assert response["ack"] == True, "Server did not acknowledge a command"

        
class ServiceMessageBroker:
    def __init__(self):
        self.remote_handler = crowdai_api.events.CrowdAIEvents()
        self.oracle_handler = crowdai_api.events.CrowdAIEvents(with_oracle=True)

    def send_game_file(self, game_file_path):
        self.remote_handler.send_blocking_call_response({
            "game_file" : game_file_path
        })
    
    def acknowledge_command(self):
        self.remote_handler.send_blocking_call_response({
            "ack" : True
        })
        
        
