# 验证 HITL "no" 分支：人工拒绝后，工具不应执行
from ReAct_langgraph import app
from langgraph.types import Command

config = {"configurable": {"thread_id": "test_no"}}

# 第一次 invoke：会停在 approve 节点的 interrupt
app.invoke({"messages": "查 WH-1000XM5 的库存"}, config=config)

# 人工选 no
final = app.invoke(Command(resume="no"), config=config)

content = final["messages"][-1].content
print("最终消息：", content)

if "拒绝" in content and "15" not in content:
    print("PASS：工具未执行，no 分支短路成功")
else:
    print("FAIL：no 分支可能没拦住工具，请检查")
