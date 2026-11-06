# -*- coding: utf-8 -*-
"""项目3 自测：多工具任务完成率 + 工具选择正确率（HITL 自动放行）。
结果写到 D:\\ai agent\\量化结果-项目3.md，同时打印控制台。
"""
import sys, time
from pathlib import Path
from dotenv import load_dotenv

BASE = Path(__file__).resolve().parent      # project3-multi-tool-agent/
ROOT = BASE.parent.parent                    # D:\ai agent\
load_dotenv(ROOT / ".env")

sys.path.insert(0, str(BASE))
from ReAct_langgraph import app   # 已编译，approve 节点用 interrupt() 做 HITL
from langgraph.types import Command

# (任务, 期望答案含这些子串, 期望调用的工具)
TASKS = [
    ("算 (15+3)*2 等于多少", ["36"], ["calculator"]),
    ("WH-1000XM5 的库存是多少", ["15"], ["query_db"]),
    ("白皮书里 BM25 能把检索失败率降到多少", ["2.9"], ["search_doc"]),
    ("把 你好 翻译成英文", ["hello"], ["translate"]),
    ("无线耳机里库存最多的是哪一款", ["QC45"], ["query_db"]),
    ("算(15+3)*2 再查 WH-1000XM5 库存 再翻译 疑是银河落九天", ["36", "15"], ["calculator", "query_db", "translate"]),
]

lines = []
def log(s=""):
    print(s)
    lines.append(s)

def run_task(task):
    config = {"configurable": {"thread_id": f"t{time.time_ns()}"}}
    result = app.invoke({"messages": task}, config=config)
    approve = 0
    while "__interrupt__" in result:
        approve += 1
        result = app.invoke(Command(resume="yes"), config=config)
    msgs = result["messages"]
    used = []
    for m in msgs:
        if getattr(m, "type", "") == "tool":
            used.append(getattr(m, "name", "?"))
    final = msgs[-1].content if hasattr(msgs[-1], "content") else str(msgs[-1])
    return final, used, approve

log("=== 项目3 多工具任务自测（HITL 自动放行） ===")
done = 0
tool_ok = 0
for q, expect, expect_tools in TASKS:
    t0 = time.time()
    try:
        final, used, approve = run_task(q)
        dt = (time.time() - t0) * 1000
    except Exception as e:
        log(f"[出错] {q} -> {type(e).__name__}: {e}")
        log("-" * 70)
        continue
    ans_ok = all(s.lower() in final.lower() for s in expect)
    t_ok = all(t in used for t in expect_tools)
    done += ans_ok
    tool_ok += t_ok
    log(f"Q: {q}")
    log(f"   期望答案含 {expect} | 答: {final}")
    log(f"   调用工具: {used} | 期望工具: {expect_tools}")
    log(f"   答案对={ans_ok} 工具对={t_ok} | 审批{approve}次 | {dt:.0f}ms")
    log("-" * 70)

log("")
log("=== 汇总（供讲稿第4问） ===")
log(f"任务完成率: {done}/{len(TASKS)}")
log(f"工具选择正确率: {tool_ok}/{len(TASKS)}")

out = ROOT / "量化结果-项目3.md"
out.write_text("\n".join(lines), encoding="utf-8")
print(f"\n结果已写入: {out}")
