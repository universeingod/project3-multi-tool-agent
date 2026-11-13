from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.types import interrupt, Command
from langchain_core.messages import AIMessage
from dotenv import load_dotenv
import os
import re
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "project2-rag-qa"))
from main import top_K   # type: ignore

load_dotenv()


@tool
def calculator(expression: str) -> str:
    """计算一个数学表达式，如 "3.5 * 2 + 1"。"""
    if not re.fullmatch(r"[0-9+\-*/().%\s]+", expression):
        return "表达式含非法字符，拒绝计算"
    try:
        return str(eval(expression))
    except Exception as e:
        return f"计算出错 {e}"

# 建一个内存数据库 + 商品表，塞入 mock 数据（每次运行都是干净的，不留文件）
conn = sqlite3.connect(":memory:", check_same_thread=False)
conn.execute("""
    CREATE TABLE products (
        id TEXT PRIMARY KEY,
        category TEXT,
        name TEXT,
        stock INT,
        price REAL,
        popularity INT
    )
""")
conn.execute("INSERT INTO products VALUES ('WH-1000XM5', '无线耳机', '索尼降噪耳机', 15, 1999.0, 95)")
conn.execute("INSERT INTO products VALUES ('QC45', '无线耳机', 'Bose降噪耳机', 26, 1499.0, 88)")
conn.execute("INSERT INTO products VALUES ('GPW', '游戏鼠标', '罗技鼠标', 12, 899.0, 90)")
conn.execute("INSERT INTO products VALUES ('VIPER', '游戏鼠标', '雷蛇鼠标', 30, 699.0, 87)")


@tool
def query_db(sql: str) -> str:
    """用 SQL 查询本地商品数据库，返回结果（文本表格）。
    表名是 products，字段有：id(商品ID)、category(类别)、name(名称)、stock(库存)、price(价格)、popularity(热度)。
    例：SELECT stock FROM products WHERE id = 'WH-1000XM5'
    """
    try:
        cur = conn.execute(sql)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description] if cur.description else []
        if not rows:
            return "（无结果）"
        return "\n".join(
            [" | ".join(cols)] +
            [" | ".join(str(x) for x in r) for r in rows]
        )
    except Exception as e:
        return f"SQL 执行出错: {e}"

@tool
def search_doc(query : str) ->str:
    """在企业RAG白皮书知识库中检索到相关片段，根据用户问题query返回相关页码+片段。
    Args:
        query : 需要检索的用户的问题
    """
    docs, metas = top_K(query, k=3)
    result = ""
    for i, (doc, meta) in enumerate(zip(docs, metas)):
        result += f"[来源{i + 1} | 第{meta['page']}页]\n{doc}\n\n"
    return result

@tool
def translate(text : str) -> str:
    """如果文本是中文就翻译成英文，如果文本是英文就翻译成中文，如果是其它语言，均翻译成中文
        Args:
            text : 待翻译的文本
    """
    llm = ChatOpenAI(
        model = "deepseek-chat",
        api_key = os.getenv("DEEPSEEK_API_KEY"),
        base_url = "https://api.deepseek.com",
        temperature=0,
        )
    prompt = f"只翻译，中文翻译英文，英文翻译中文，其它语言翻译成中文，不解释{text}"
    res = llm.invoke(prompt)
    return res.content

tools = [calculator, query_db, search_doc, translate]

class AgentState(TypedDict):
    messages : Annotated[List, add_messages]

def agent(state : AgentState):
    llm = ChatOpenAI(
    model = "deepseek-chat",
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    base_url = "https://api.deepseek.com",
    )
    print("流到了agent")
    return {"messages" : [llm.bind_tools(tools).invoke(state["messages"])]}

def route_tools(state : AgentState):
    msg = state["messages"][-1]
    if msg.tool_calls:
        print("流到了tools")
        return "tools"
    print("流到了END")
    return END


def approve(state : AgentState):
    """工具调用前的人工审批：interrupt 暂停，resume 传入 yes/no。"""
    decision = interrupt("待执行工具调用，是否批准？(yes/no)")
    if str(decision).strip().lower() != "yes":
        return {"messages" : [AIMessage(content="[系统] 人工拒绝了本次工具调用")]}
    return {}


def route_after_approve(state : AgentState):
    """审批后路由：yes → 执行工具；no → 短路，不执行工具直接结束。"""
    if state["messages"][-1].content == "[系统] 人工拒绝了本次工具调用":
        print("审批被拒绝，工具未执行")
        return END
    return "tools"


builder = StateGraph(AgentState)
builder.add_node("agent", agent)
builder.add_node("approve", approve)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_tools, {"tools" : "approve", END : END})
builder.add_conditional_edges("approve", route_after_approve, {"tools" : "tools", END : END})
builder.add_edge("tools", "agent")

checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    # Human-in-the-loop：approve 节点里 interrupt() 暂停，等人工审批；resume 用 Command(resume="yes")
    config = {"configurable": {"thread_id": "1"}}
    result = app.invoke({"messages": "算 (15+3)*2 再查 WH-1000XM5 库存 再翻译“疑是银河落九天”"}, config=config)
    approve_count = 0
    while "__interrupt__" in result:
        approve_count += 1
        print(f"【HITL】第 {approve_count} 次工具调用待人工审批（本 demo 自动放行 yes）")
        result = app.invoke(Command(resume="yes"), config=config)

    print("模型回答：", result["messages"][-1].content)
    print(f"（HITL 工具调用审批次数：{approve_count}）")

    print(app.get_graph().draw_mermaid())