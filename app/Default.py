# Welcome to
# __________         __    __  .__                               __
# \______   \_____ _/  |__/  |_|  |   ____   ______ ____ _____  |  | __ ____
#  |    |  _/(__  \\   __\   __\  | _/ __ \ /  ___//    \\__  \ |  |/ // __ \
#  |    |   \ / __ \|  |  |  | |  |_\  ___/ \___ \|   |  \/ __ \|    <\  ___/
#  |________/(______/__|  |__| |____/\_____>______>___|__(______/__|__\\_____>
#
# This file can be a nice home for your Battlesnake logic and helper functions.
#
# To get you started we've included code to prevent your Battlesnake from moving backwards.
# For more info see docs.battlesnake.com

import random
import typing
import threading

from app.BattleSnakeServer import get_move_override
from app.BattleSnakeServer import run_server

VALID_MOVES = {"up", "down", "left", "right"}


# info is called when you create your Battlesnake on play.battlesnake.com
# and controls your Battlesnake's appearance
# TIP: If you open your Battlesnake URL in a browser you should see this data
def info() -> typing.Dict:
    print("INFO")

    return {
        "apiversion": "1",
        "author": "",  # TODO: Your Battlesnake Username
        "color": "#888888",  # TODO: Choose color
        "head": "default",  # TODO: Choose head
        "tail": "default",  # TODO: Choose tail
    }


# start is called when your Battlesnake begins a game
def start(game_state: typing.Dict):
    print("GAME START")


# end is called when your Battlesnake finishes a game
def end(game_state: typing.Dict):
    print("GAME OVER\n")


# move is called on every turn and returns your next move
# Valid moves are "up", "down", "left", or "right"
# See https://docs.battlesnake.com/api/example-move for available data
def _default_move(game_state: typing.Dict) -> typing.Dict:
    is_move_safe = {"up": True, "down": True, "left": True, "right": True}

    my_head = game_state["you"]["body"][0]
    my_neck = game_state["you"]["body"][1]

    if my_neck["x"] < my_head["x"]: is_move_safe["left"] = False
    elif my_neck["x"] > my_head["x"]: is_move_safe["right"] = False
    elif my_neck["y"] < my_head["y"]: is_move_safe["down"] = False
    elif my_neck["y"] > my_head["y"]: is_move_safe["up"] = False

    board_width = game_state['board']['width']
    board_height = game_state['board']['height']

    if my_head["x"] == 0: is_move_safe["left"] = False
    if my_head["x"] == board_width - 1: is_move_safe["right"] = False
    if my_head["y"] == 0: is_move_safe["down"] = False
    if my_head["y"] == board_height - 1: is_move_safe["up"] = False

    my_body = game_state['you']['body']
    opponents = game_state['board']['snakes']

    for move in is_move_safe.keys():
        if not is_move_safe[move]: continue
        next_coord = my_head.copy()
        if move == "up": next_coord["y"] += 1
        elif move == "down": next_coord["y"] -= 1
        elif move == "left": next_coord["x"] -= 1
        elif move == "right": next_coord["x"] += 1

        if next_coord in my_body:
            is_move_safe[move] = False

        for snake in opponents:
            if next_coord in snake["body"]:
                is_move_safe[move] = False

    safe_moves = [m for m, safe in is_move_safe.items() if safe]

    if len(safe_moves) == 0:
        print(f"MOVE {game_state['turn']}: No safe moves detected! Moving down")
        return {"move": "down"}

    food = game_state['board']['food']
    if food:
        nearest_food = min(food, key=lambda f: abs(f['x'] - my_head['x']) + abs(f['y'] - my_head['y']))
        best_move = None
        min_dist = 9999
        for move in safe_moves:
            next_coord = my_head.copy()
            if move == "up": next_coord["y"] += 1
            elif move == "down": next_coord["y"] -= 1
            elif move == "left": next_coord["x"] -= 1
            elif move == "right": next_coord["x"] += 1
            dist = abs(next_coord['x'] - nearest_food['x']) + abs(next_coord['y'] - nearest_food['y'])
            if dist < min_dist:
                min_dist = dist
                best_move = move
        next_move = best_move
    else:
        next_move = random.choice(safe_moves)

    print(f"MOVE {game_state['turn']}: {next_move}")
    return {"move": next_move}


def move(game_state: typing.Dict) -> typing.Dict:
    override_move = get_move_override()

    if override_move is not None:
        try:
            override_response = override_move(game_state)
            if (
                isinstance(override_response, dict)
                and override_response.get("move") in VALID_MOVES
            ):
                return override_response

            raise ValueError(
                "Override move must return a dict like {'move': 'up'}."
            )
        except Exception as exc:
            print(
                f"MOVE {game_state['turn']}: override failed ({exc}). "
                "Falling back to default logic."
            )

    return _default_move(game_state)


# Start server when `python main.py` is run
if __name__ == "__main__":
    handlers = {"info": info, "start": start, "move": move, "end": end}
    # Run the first server in a separate thread
    threading.Thread(target=run_server, args=(handlers, 8000), daemon=True).start()
    # Run the second server in the main thread
    run_server(handlers, 8001)