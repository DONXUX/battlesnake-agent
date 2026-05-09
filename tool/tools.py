import requests
import subprocess
import re
from langchain.tools import tool

@tool
def update_battlesnake_script(script: str) -> str:
    """
    Updates the move logic for the Battlesnake server on port 8001,
    then runs a match against the server on port 8000 to see who wins.
    If port 8001 wins, updates port 8000 with the new script.
    Args:
        script: The Python code string containing the move logic.
    Returns:
        A string indicating the update status and the winner.
    """
    update_url_8001 = "http://localhost:8001/update_move"
    update_url_8000 = "http://localhost:8000/update_move"
    try:
        # 1. Update and Validate the script on port 8001
        resp = requests.post(update_url_8001, data=script.encode('utf-8'))
        if resp.status_code != 200:
            err_msg = resp.json().get('message', 'Unknown error') if resp.headers.get('Content-Type') == 'application/json' else resp.text
            return f"Validation Failed for port 8001 update: {err_msg}"

        # 2. Run the match using the CLI
        cmd = [
            "/Users/donguklee/Development/Project/battle-snake-agent/rules/battlesnake", "play",
            "-u", "http://localhost:8000",
            "-u", "http://localhost:8001",
            "-W", "11", "-H", "11"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr

        # 3. Determine which name corresponds to which port
        name_8000 = re.search(r"URL: http://localhost:8000, Name: \"(.*?)\"", output)
        name_8001 = re.search(r"URL: http://localhost:8001, Name: \"(.*?)\"", output)

        # 4. Parse the winner name
        winner_match = re.search(r"turns\. (.*) was the winner\.", output)

        if winner_match:
            winner_name = winner_match.group(1).strip()
            if name_8000 and winner_name == name_8000.group(1):
                return "Winner: Port 8000. Your new script lost; existing 8000 script maintained."
            elif name_8001 and winner_name == name_8001.group(1):
                # Update port 8000 with the winning script
                upd_resp = requests.post(update_url_8000, data=script.encode('utf-8'))
                if upd_resp.status_code == 200:
                    return "Winner: Port 8001! Your new script won and Port 8000 has been updated."
                else:
                    return f"Winner: Port 8001, but failed to update Port 8000. Status: {upd_resp.status_code}"
            else:
                return f"Winner name: {winner_name} (Could not map to port)"
        else:
            return f"Could not determine winner. Output: {output[:150]}..."

    except Exception as e:
        return f"An error occurred: {str(e)}"


@tool
def get_current_battlesnake_script() -> str:
    """
    Retrieves the current move logic from the Battlesnake server running on port 8000.
    Returns:
        A string containing the Python code of the current move logic.
    """
    url = "http://localhost:8000/move"
    try:
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.text
        else:
            return f"Failed to retrieve script. Status: {resp.status_code}"
    except Exception as e:
        return f"An error occurred while fetching the script: {str(e)}"


docs=r"""
<battlesnake_docs_start>
# Webhooks

This page documents the technical details of the webhooks sent from the game engine to your Battlesnake server. They all originate from the Battlesnake Server URL that you provide when creating your Battlesnake in the dashboard.


## Move

HTTP Request: `POST /move`

This request will be sent for every turn of every game that your Battlesnake plays. Use the information provided to determine how your Battlesnake will move on that turn, either up, down, left, or right.

#### Request Parameters

| **Parameter**                      | **Type** | **Description**                                                               |
| ---------------------------------- | -------- | ----------------------------------------------------------------------------- |
| **game**                           | object   | [Game Object](objects/game) describing the game being played.                 |
| **turn**                           | integer  | Turn number for this move.                                                    |
| **board**                          | object   | [Board Object](objects/board) describing the initial state of the game board. |
| **you**                            | object   | [Battlesnake Object](objects/battlesnake) describing your Battlesnake.        |


#### Response Properties

| **Property**  | **Type**            | **Description**                                                                                      |
| ------------- | ------------------- | ---------------------------------------------------------------------------------------------------- |
| **move**      | string              | Your Battlesnake's move for this turn. Valid moves are "up", "down", "left", or "right".             |
| **shout**     | string _(optional)_ | An optional message sent to all other Battlesnakes on the next turn. Must be 256 characters or less. |


#### Example Response

```json title="200 OK"
{
  "move": "up",
  "shout": "Moving up!"
}
```

# Board

The game board is represented by a standard 2D grid, oriented with (0,0) in the bottom left. The Y-Axis is positive in the up direction, and X-Axis is positive to the right. Coordinates begin at zero, such that a board that is 11x11 will have coordinates ranging from [0, 10].

```json
{
  "height": 11,
  "width": 11,
  "food": [
    {"x": 5, "y": 5},
    {"x": 9, "y": 0},
    {"x": 2, "y": 6}
  ],
  "hazards": [
    {"x": 0, "y": 0},
    {"x": 0, "y": 1},
    {"x": 0, "y": 2}
  ],
  "snakes": [
    {"id": "snake-one", ... },
    {"id": "snake-two", ... },
    {"id": "snake-three", ... }
  ]
}
```

| **Property** | **Type** | **Description**                                                                                                                                                                                                       |
| ------------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **height**   | integer  | The number of rows in the y-axis of the game board. <em>Example: 11</em>                                                                                                                                              |
| **width**    | integer  | The number of columns in the x-axis of the game board. <em>Example: 11</em>                                                                                                                                           |
| **food**     | array    | Array of coordinates representing food locations on the game board. <em>Example: [{"x": 5, "y": 5}, ..., {"x": 2, "y": 6}]</em>                                                                                       |
| **hazards**  | array    | Array of coordinates representing hazardous locations on the game board. <em>Example: [{"x": 0, "y": 0}, ..., {"x": 0, "y": 1}]</em>            |
| **snakes**   | array    | Array of [Battlesnake Objects](./battlesnake) representing all Battlesnakes remaining on the game board (including yourself if you haven't been eliminated). <em>Example: [{"id": "snake-one", ...}, ...]</em>       |

# Battlesnake

```json
{
  "id": "totally-unique-snake-id",
  "name": "Sneky McSnek Face",
  "health": 54,
  "body": [
    {"x": 0, "y": 0},
    {"x": 1, "y": 0},
    {"x": 2, "y": 0}
  ],
  "latency": "123",
  "head": {"x": 0, "y": 0},
  "length": 3,
  "shout": "why are we shouting??",
  "squad": "1",
  "customizations":{
    "color":"#26CF04",
    "head":"smile",
    "tail":"bolt"
  }
}
```

| **Property**       | **Type** | **Description**                                                                                                                                                                                                                         |
| ------------------ | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **id**             | string   | Unique identifier for this Battlesnake in the context of the current Game. <em>Example: "totally-unique-snake-id"</em>                                                                                                                   |
| **name**           | string   | Name given to this Battlesnake by its author. <em>Example: "Sneky McSnek Face"</em>                                                                                                                                                      |
| **health**         | integer  | Health value of this Battlesnake, between 0 and 100 inclusively. <em>Example: 54</em>                                                                                                                                                    |
| **body**           | array    | Array of coordinates representing this Battlesnake's location on the game board. This array is ordered from head to tail. <em>Example: [{"x": 0, "y": 0}, ..., {"x": 2, "y": 0}]</em>                                                    |
| **latency**        | string   | The previous response time of this Battlesnake, in milliseconds. If the Battlesnake timed out and failed to respond, the game timeout will be returned (<code>game.timeout</code>) <em>Example: "500"</em>                               |
| **head**           | object   | Coordinates for this Battlesnake's head. Equivalent to the first element of the body array. <em>Example: {"x": 0, "y": 0}</em>                                                                                                           |
| **length**         | integer  | Length of this Battlesnake from head to tail. Equivalent to the length of the body array. <em>Example: 3</em>                                                                                                                            |
| **shout**          | string   | Message shouted by this Battlesnake on the previous turn. <em>Example: "why are we shouting??"</em>                                                                                                                                      |
| **squad**          | string   | The squad that the Battlesnake belongs to. Used to identify squad members in Squad Mode games. <em>Example: "1"</em>                                                                                                                     |
| **customizations** | object   | The collection of customizations that control how this Battlesnake is displayed. _Example: {"color":"#888888", "head":"default", "tail":"default" }_ |

# Example Move Request

### Move Request

```json title="POST /move"
{
  "game": {
    "id": "totally-unique-game-id",
    "ruleset": {
      "name": "standard",
      "version": "v1.1.15",
      "settings": {
        "foodSpawnChance": 15,
        "minimumFood": 1,
        "hazardDamagePerTurn": 14
      }
    },
    "map": "standard",
    "source": "league",
    "timeout": 500
  },
  "turn": 14,
  "board": {
    "height": 11,
    "width": 11,
    "food": [
      {"x": 5, "y": 5},
      {"x": 9, "y": 0},
      {"x": 2, "y": 6}
    ],
    "hazards": [
      {"x": 3, "y": 2}
    ],
    "snakes": [
      {
        "id": "snake-508e96ac-94ad-11ea-bb37",
        "name": "My Snake",
        "health": 54,
        "body": [
          {"x": 0, "y": 0},
          {"x": 1, "y": 0},
          {"x": 2, "y": 0}
        ],
        "latency": "111",
        "head": {"x": 0, "y": 0},
        "length": 3,
        "shout": "why are we shouting??",
        "customizations":{
          "color":"#FF0000",
          "head":"pixel",
          "tail":"pixel"
        }
      },
      {
        "id": "snake-b67f4906-94ae-11ea-bb37",
        "name": "Another Snake",
        "health": 16,
        "body": [
          {"x": 5, "y": 4},
          {"x": 5, "y": 3},
          {"x": 6, "y": 3},
          {"x": 6, "y": 2}
        ],
        "latency": "222",
        "head": {"x": 5, "y": 4},
        "length": 4,
        "shout": "I'm not really sure...",
        "customizations":{
          "color":"#26CF04",
          "head":"silly",
          "tail":"curled"
        }
      }
    ]
  },
  "you": {
    "id": "snake-508e96ac-94ad-11ea-bb37",
    "name": "My Snake",
    "health": 54,
    "body": [
      {"x": 0, "y": 0},
      {"x": 1, "y": 0},
      {"x": 2, "y": 0}
    ],
    "latency": "111",
    "head": {"x": 0, "y": 0},
    "length": 3,
    "shout": "why are we shouting??",
    "customizations": {
      "color":"#FF0000",
      "head":"pixel",
      "tail":"pixel"
    }
  }
}
```

### Move Response

```json title="200 OK"
{
  "move": "up",
  "shout": "I guess I'll go up then."
}
```

<battlesnake_docs_end>
"""