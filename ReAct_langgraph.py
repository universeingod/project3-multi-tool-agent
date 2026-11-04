from typing import Annotated, List, TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
import os
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "project2-rag-qa"))
from main import top_K   # type: ignore

load_dotenv()

llm = ChatOpenAI(
    model = "deepseek-chat",
    api_key = os.getenv("DEEPSEEK_API_KEY"),
    base_url = "https://api.deepseek.com",
)
@tool
def calculator(expression: str) -> float:
    """计算一个数学表达式，如 "3.5 * 2 + 1"。"""
    return eval(expression)

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


tools = [calculator, query_db, search_doc]

class AgentState(TypedDict):
    messages : Annotated[List, add_messages]

def agent(state : AgentState):
    print("流到了agent")
    return {"messages" : [llm.bind_tools(tools).invoke(state["messages"])]}

def route_tools(state : AgentState):
    msg = state["messages"][-1]
    if msg.tool_calls:
        print("流到了tools")
        return "tools"
    print("流到了END")
    return END

builder = StateGraph(AgentState)
builder.add_node("agent", agent)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", route_tools, {"tools" : "tools", END : END})
builder.add_edge("tools", "agent")

app = builder.compile()

result = app.invoke({"messages" : "算 (15+3)*2 再查 WH-1000XM5 库存"})
print("模型回答：", result["messages"][-1].content)

print(app.get_graph().draw_mermaid())