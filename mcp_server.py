from mcp.server.fastmcp import FastMCP
from datetime import datetime
import sys
from pathlib import Path

# 把 project2 的目录加进搜索路径，才能 from main import top_K
PROJECT2_DIR = Path(__file__).resolve().parent.parent / "project2-rag-qa"
sys.path.insert(0, str(PROJECT2_DIR))

from main import top_K  # type: ignore

mcp = FastMCP("Demo")

@mcp.tool()
def add(a : int, b : int) ->int:
    """求两数之和
    Args:
        a : 第一个整数
        b : 第二个整数
    """
    return a + b

@mcp.tool()
def get_now() ->str:
    """获取服务器当前本地时间，格式 YYYY-MM-DD HH:MM:SS"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@mcp.tool()
def echo(text : str) -> str:
    """回显文本，返回原样的文本
    Args:
        text : 需要回显的文本
    """
    return text

@mcp.tool()
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


if __name__ == "__main__":
    mcp.run(transport = "stdio")