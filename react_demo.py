from openai import OpenAI
from dotenv import load_dotenv
import os
import json
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

PRODUCT_DB = {
    "无线耳机": [{"id": "WH-1000XM5", "popularity": 95},
                 {"id": "QC45",       "popularity": 88}],
    "游戏鼠标": [{"id": "GPW",  "popularity": 90},
                 {"id": "VIPER", "popularity": 87}],
}
WH = {"WH-1000XM5" : 15, "QC45" : 26, "GPW" : 12, "VIPER" : 30}

def get_top_product(category : str) -> str:
    """返回最热门的指定商品的id
    Args:
        category : 指定商品的名称
    """
    products = PRODUCT_DB[category]
    top = max(products, key=lambda p: p["popularity"])
    return top["id"]

def get_stock(product_id : str) -> int:
    """返回指定商品的数量
    Args:
        product_id : 指定商品的名字
    """
    numb = WH[product_id]
    return numb
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_top_product",          # 必须和 def get_top_product 一致
            "description": "返回指定商品类别中最热门的商品 id",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string",
                                 "description": "商品类别，如 无线耳机、游戏鼠标"}
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock",                # 必须和 def get_stock 一致
            "description": "返回指定商品 id 的库存数量",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "string",
                                   "description": "商品 id，如 WH-1000XM5"}
                },
                "required": ["product_id"]
            }
        }
    }
]

USER = "无线耳机里最热门的商品，现在库存还有多少？"
messages = [{"role" : "system", "content" : ""},
            {"role" : "user", "content" : USER},
            ]


while(True):
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools,
            temperature=0.7,
            max_tokens=1024,
            stream=False,
        )
        msg = response.choices[0].message
        if msg.tool_calls:
            messages.append(
                {
                    "role" : "assistant",
                    "content" : msg.content,  #在这次因为想调工具，所以content为None
                    "tool_calls" : [
                        {
                            "id" : tc.id, "type" : "function", 
                            "function" : {"name" : tc.function.name, "arguments" : tc.function.arguments}
                        }
                        for tc in msg.tool_calls
                    ],
                }
            )
            for tc in msg.tool_calls:
                arg = json.loads(tc.function.arguments)
                print("🔧 调用工具:", tc.function.name, "参数:", tc.function.arguments)
                if tc.function.name == "get_top_product":
                    result = get_top_product(arg["category"])
                elif tc.function.name == "get_stock":
                    result = get_stock(arg["product_id"])

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),        # 注意 str()，get_stock 返回的是 int
                })
        else:
            print("最终答案或不需要调用tool的答案:", msg.content)
            break


    except Exception as e:
        raise e
