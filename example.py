import textworld
import textworld_remote_env


agent = textworld.agents.NaiveAgent()
remote_env = textworld_remote_env.RemoteEnv()
while True:
    env = remote_env.start()
    print(env)
    if env == False:
        """
            Evaluator will continue submitting new envs
            and whenever it is done submitting new envs,
            it will send a False to break out of the loop
        """
        break
    
    agent.reset(env)  # Tell the agent a new episode is starting.
    game_state = env.reset()  # Start new episode.
    print(game_state)
    reward = 0
    done = False
    for k in range(100):
        command = agent.act(game_state, reward, done)
        game_state, reward, done = env.step(command)
        print(game_state, reward, done)
        if done:
            break
    
    print("Number of moves : ", game_state.nb_moves)
    print("Score : ", game_state.score)
    env.close()
