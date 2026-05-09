import os
from datetime import datetime
import dotenv
from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from tool.tools import update_battlesnake_script, get_current_battlesnake_script, docs

# Ensure the Battlesnake tools are imported
from __main__ import update_battlesnake_script, get_current_battlesnake_script, docs

# 환경변수 설정
dotenv.load_dotenv(override=True)
# Colab 환경변수 로드
# from google.colab import userdata
# os.environ["OPENAI_API_KEY"] = userdata.get("openrouter")

# api_key = os.environ["OPENAI_API_KEY"]
api_key = os.getenv("OPENAI_API_KEY")
base_url = "https://openrouter.ai/api/v1"

if not api_key:
    raise ValueError("OPENAI_API_KEY 환경변수가 필요합니다.")

# Battlesnake Agent Instructions
BATTLESNAKE_AGENT_INSTRUCTIONS = \
    f"""당신은 Battlesnake 봇의 move 스크립트를 개선하는 AI 에이전트입니다. 
    Battlesnake 게임의 목표는 가장 오래 생존하는 것입니다.

    <Task>
    당신의 임무는 현재 move 스크립트를 분석하고, 
    Battlesnake 게임의 규칙과 전략에 따라 더 나은 스크립트를 제안하여 
    'update_battlesnake_script' 도구를 사용하여 기존 스크립트와 대결하게 하는 것입니다. 
    만약 새로운 스크립트가 승리하면 그 스크립트를 최종 스크립트로 업데이트해야 합니다. 패배하면 기존 스크립트를 유지하고 새로운 개선안을 시도해야 합니다.
    </Task>
    
    <Available Tools>
    1. `get_current_battlesnake_script`: 현재 실행 중인 Battlesnake 봇의 move 스크립트를 가져옵니다.
    2. `update_battlesnake_script`: 새로운 move 스크립트를 업데이트하고, 기존 스크립트와 대결하여 승패를 판단합니다. 
        승리 시 새 스크립트가 적용됩니다.
    </Available Tools>
    
    <Battlesnake API Docs>
    {docs}
    </Battlesnake API Docs>
    
    <Instructions>
    다음 단계를 따르세요:
    1. `get_current_battlesnake_script`를 사용하여 현재 봇의 move 스크립트를 가져옵니다.
    2. 가져온 스크립트와 위에 제공된 Battlesnake API 문서를 기반으로 스크립트를 개선할 전략을 수립합니다. 
        예를 들어, 먹이를 효율적으로 찾아가는 방법, 벽이나 자기 몸에 부딪히지 않는 방법, 다른 뱀을 피하거나 공격하는 방법 등을 고려할 수 있습니다.
    3. 개선된 `move` 함수를 포함하는 새로운 Python 스크립트 코드를 작성합니다. 
        이 스크립트는 Battlesnake API의 `game_state` 객체를 입력으로 받고 {{ "move": "up" }}와 같은 딕셔너리를 반환해야 합니다.
    4. `update_battlesnake_script` 도구를 사용하여 새로운 스크립트를 제출합니다.
    5. `update_battlesnake_script`의 결과를 분석합니다. 새 스크립트가 이기면 작업이 완료된 것입니다. 
        지면, 패배의 원인을 분석하고 2단계로 돌아가 스크립트를 다시 개선합니다. 최대 3번까지 스크립트 개선을 시도할 수 있습니다.
    </Instructions>
    
    <Example move function structure>
    def move(game_state):
        # Your Battlesnake logic here
        # Access game_state, board, your snake details as per docs
        # Example: my_head = game_state["you"]["body"][0]
        # Example: food = game_state["board"]["food"]
        # Return a dictionary like: {{ "move": "up", "shout": "Hello!" }}
        return {{"move": "up"}}
"""


model = init_chat_model(
    model="google/gemini-3.1-flash-lite-preview",
    model_provider="openai",
    temperature=0.0,
    api_key=api_key,
    base_url=base_url,
)

battlesnake_agent = create_deep_agent(
    model=model,
    tools=[update_battlesnake_script, get_current_battlesnake_script],
    system_prompt=BATTLESNAKE_AGENT_INSTRUCTIONS,
    subagents=[], # This agent does not use subagents for research
)

# 에이전트 실행
print("\n### DeepAgent 실행 시작 ###")
research_request = "내 Battlesnake 봇의 move 스크립트를 개선해줘. 먹이를 더 잘 찾아가고 벽에 부딪히지 않도록 해줘."
deepagent_result = battlesnake_agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": research_request,
            }
        ],
    }
)

print("\n# DeepAgent의 최종 응답입니다.")
print(deepagent_result["messages"][-1].content)

deepagent_final_script = get_current_battlesnake_script.invoke({})
print("\n# DeepAgent가 업데이트한 최종 스크립트 (Port 8000에 저장됨):\n", deepagent_final_script)

print("Battlesnake DeepAgent가 설정되었습니다. 이제 'battlesnake_agent.invoke'를 사용하여 스크립트 개선을 시작할 수 있습니다.")



