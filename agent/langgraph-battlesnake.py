import os
import dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from tool.tools import update_battlesnake_script, get_current_battlesnake_script, docs

# Ensure the Battlesnake tools are imported
from __main__ import update_battlesnake_script, get_current_battlesnake_script, docs

# 환경변수 설정
dotenv.load_dotenv(override=True)

api_key = os.getenv("OPENAI_API_KEY")
base_url = "https://openrouter.ai/api/v1"


# 1. State 정의
class BattlesnakeState(TypedDict):
    current_script: str
    proposed_script: str
    evaluation_result: str
    iterations: int


# --- LLM 설정 ---
def build_chat_model(
        model="google/gemini-3.1-flash-lite-preview",
        *,
        temperature: float = 0.3,
):
    return init_chat_model(
        model=model,
        model_provider="openai",
        temperature=temperature,
        api_key=api_key,
        base_url=base_url,
    )


model = build_chat_model()


# 2. Node 정의
def get_script_node(state: BattlesnakeState):
    print("--- [1. Get Current Script] 현재 스크립트 가져오는 중 ---")
    current_script = get_current_battlesnake_script.invoke({})  # Use invoke for tool calls
    return {"current_script": current_script, "iterations": 0}


def propose_script_node(state: BattlesnakeState):
    print(f"--- [2. Propose Script] 새로운 스크립트 제안 중 (반복: {state.get('iterations', 0)}) ---")
    current_script = state["current_script"]

    # Add a more detailed prompt for the LLM to understand the task
    prompt = ChatPromptTemplate.from_messages([
        ("system",
         """당신은 Battlesnake 게임의 전문가 AI입니다. 다음 Battlesnake API 문서를 참고하여, 주어진 현재 스크립트보다 더 나은 성능을 낼 수 있는 새로운 'move' 함수 Python 코드를 생성해야 합니다.\n현재 스크립트는 벽 충돌, 자기 몸 충돌, 기본적인 먹이 찾기 로직을 가지고 있습니다. 이를 개선하여 더 스마트한 움직임(예: 적 뱀 피하기, 적 뱀 머리 공격, 꼬리 추격, 안전한 공간 확보 등)을 하도록 만들어야 합니다.\n오직 Python 'move' 함수 코드만 응답해야 하며, 다른 설명이나 주석은 포함하지 마세요. 함수의 시그니처는 `def move(game_state):` 여야 합니다.\n\n<Battlesnake API Docs>\n{docs}\n</Battlesnake API Docs>\n\n<Current Script>\n{current_script}\n</Current Script>\n"""),
        ("human",
         "현재 Battlesnake 'move' 스크립트를 개선하여 먹이를 먹고 벽에 부딪히지 않고 더 오래 생존하고 승리할 수 있는 새로운 Python 코드를 제안해주세요. 뱀의 머리 모습은 smart-caterpillar 로 구현해줘 ")
    ])

    chain = prompt | model
    response = chain.invoke({"docs": docs, "current_script": current_script})
    # Extract only the code block if the LLM wraps it in markdown
    proposed_code = response.content.strip()
    if proposed_code.startswith("```python") and proposed_code.endswith("```"):
        proposed_code = proposed_code[len("```python\n"):-len("```")].strip()

    return {"proposed_script": proposed_code, "iterations": state.get("iterations", 0) + 1}


def evaluate_script_node(state: BattlesnakeState):
    print(f"--- [3. Evaluate Script] 스크립트 평가 중 (반복: {state.get('iterations', 0)}) ---")
    proposed_script = state["proposed_script"]
    evaluation_result = update_battlesnake_script.invoke({"script": proposed_script})  # Use invoke for tool calls
    return {"evaluation_result": evaluation_result}


def analyze_result_node(state: BattlesnakeState):
    print(f"--- [4. Analyze Result] 결과 분석 중 (반복: {state.get('iterations', 0)}) ---")
    evaluation_result = state["evaluation_result"]

    if "Winner: Port 8011!" in evaluation_result or "Winner: Port 8001!" in evaluation_result:  # Updated port to 8001, consistency.
        print("New script won! Ending improvement process.")
        return {"current_script": state["proposed_script"]}
    elif "Winner: Port 8000." in evaluation_result:
        print("New script lost. Iterating for improvement.")
        # The current script remains the one from port 8000, which is the original or the last winning one.
        # We just need to signal that we want to try again.
        return {"current_script": get_current_battlesnake_script.invoke({})}
    else:
        print(f"Evaluation inconclusive: {evaluation_result}. Iterating.")
        return {"current_script": get_current_battlesnake_script.invoke({}) if state.get(
            'current_script') else None}  # Fallback if initial current_script is not set.


# 3. 그래프 구성
workflow = StateGraph(BattlesnakeState)
workflow.add_node("get_script", get_script_node)
workflow.add_node("propose_script", propose_script_node)
workflow.add_node("evaluate_script", evaluate_script_node)
workflow.add_node("analyze_result", analyze_result_node)

workflow.add_edge(START, "get_script")
workflow.add_edge("get_script", "propose_script")
workflow.add_edge("propose_script", "evaluate_script")
workflow.add_conditional_edges(
    "evaluate_script",
    lambda state: "continue" if state["iterations"] < 10 and (
                "Winner: Port 8000." in state["evaluation_result"] or "Evaluation inconclusive" in state[
            "evaluation_result"]) else "end",
    {
        "continue": "propose_script",  # Loop back to propose if not enough iterations and did not win
        "end": "analyze_result",  # Go to analyze result to determine final outcome
    },
)
workflow.add_edge("analyze_result", END)

# 4. 실행
app = workflow.compile()

print("Battlesnake LangGraph Agent가 설정되었습니다. 이제 'app.invoke'를 사용하여 스크립트 개선을 시작할 수 있습니다.")
# 예시 실행 코드 (주석 처리)
query = {"topic": "Battlesnake move script improvement"}
result = app.invoke(query)
print("\n[최종 스크립트 개선 결과]:")
print(result["evaluation_result"])
