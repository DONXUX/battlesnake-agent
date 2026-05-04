import json
import logging
import random
import textwrap
import threading
import typing

from flask import Flask, request, Response, jsonify


# Callable[[인자1, 인자2, ...], 반환]
MoveHandler = typing.Callable[[dict], dict]

_move_override_lock = threading.Lock()
_move_override: typing.Optional[MoveHandler] = None


# Battle Snake Default Server Script
# https://github.com/BattlesnakeOfficial/starter-snake-python/blob/main/main.py
DEFAULT_LOGIC = """def move(game_state):
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
    """


_current_script: str = DEFAULT_LOGIC


# 실행될 코드가 사용할 namespace 딕셔너리를 만들어 반환하는 함수
#
# [사용 예시]
#   namespace = _build_move_namespace()
#   exec("""
#   value = random.choice([1, 2, 3])
#   """, namespace)
#
#   print(namespace["value"])
def _build_move_namespace() -> typing.Dict[str, typing.Any]:
    return {
        "__builtins__": __builtins__,   ## 파이썬 기본 내장 함수/객체
        "random": random,               ## random 모듈
        "typing": typing,               ## typing 모듈
    }


# DEFAULT_LOGIC 코드를 한번 더 감쌈. textwrap을 이용해 4칸 들여쓰기
# def move(game_state):
#   def move(game_state):
#       ...
def _wrap_move_body(script: str) -> str:
    return "def move(game_state):\n" + textwrap.indent(script, "    ") + "\n"


# 전달된 파이썬 코드를 실행하여, 그 안에 move 함수를 찾아 실행 가능한 핸들러로 만들어 반환한다.
# 즉, 사용자가 작성한 move 로직을 문자열로 받아서 실제 파이썬 함쉋럼 쓸 수 있게 Compile -> Load 한다.
def _compile_move_override(script: str) -> MoveHandler:
    attempts = [("module", script), ("body", _wrap_move_body(script))]
    last_err = ""
    for mode, candidate in attempts:
        namespace = _build_move_namespace()
        try:
            exec(candidate, namespace, namespace)
            move_handler = namespace.get("move")
            if callable(move_handler):
                return typing.cast(MoveHandler, move_handler), mode
        except Exception as e:
            last_err = str(e)
            continue
    raise ValueError(f"Invalid move script: {last_err}")


# 사용자가 전달한 script 문자열을 새로운 move 로직으로 등록하거나, 빈 문자열이면 override를 햊하는 함수
# 즉, 기본 이동 로직 대신 사용할 커스텀 move 함수를 설정하는 역할
def set_move_override(script: str) -> str:
    global _move_override, _current_script
    with _move_override_lock:
        if not script.strip(): ## 빈 문자열인 경우 Clear
            _move_override, _current_script = None, DEFAULT_LOGIC
            return "cleared"
        move_handler, mode = _compile_move_override(script)
        _move_override, _current_script = move_handler, script
        return mode


def get_move_override() -> typing.Optional[MoveHandler]:
    with _move_override_lock: return _move_override


# Flask Application 생성
def create_app(handlers: typing.Dict):
    app = Flask("Battlesnake")

    @app.route("/", methods=["GET"])
    def on_info(): return jsonify(handlers["info"]())

    @app.route("/start", methods=["POST"])
    def on_start():
        handlers["start"](request.get_json())
        return "ok"

    @app.route("/move", methods=["GET"])
    def get_move(): return Response(_current_script, mimetype="text/plain")

    @app.route("/move", methods=["POST"])
    def on_move(): return jsonify(handlers["move"](request.get_json()))

    @app.route("/update_move", methods=["POST"])
    def on_update_move():
        raw = request.get_data().decode("utf-8")
        try: payload = json.loads(raw)
        except: payload = None
        script = payload.get("script") if isinstance(payload, dict) else raw
        try:
            mode = set_move_override(script)
            return jsonify({"status": "ok", "mode": mode})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/end", methods=["POST"])
    def on_end():
        handlers["end"](request.get_json())
        return "ok"

    return app


# 서버 실행
def run_server(handlers: typing.Dict, port: int = 8000) -> None:
    app = create_app(handlers)
    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    print(f"Running Battlesnake (Flask) at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, threaded=False)