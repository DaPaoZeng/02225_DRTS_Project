import pandas as pd, os, math
import config

"""simulate_full_auto.py — 两级分层仿真 (Deadline‑miss fix + verbose)"""

QUANTUM   = 1.0    # 执行粒度 (TU)
SIM_TIME  = 5000   # 仿真总时长 (TU)
EPS       = 1e-6   # 浮点容差

# --------------------------------------------------
# 读取输入
# --------------------------------------------------
tasks_df  = pd.read_csv(config.TASKS_PATH)
arch_df   = pd.read_csv(config.ARCH_PATH)
supply_df = pd.read_csv(config.RESOURCE_SUPPLY_PATH)
print(f"=== Simulator: tasks={len(tasks_df)}, cores={len(arch_df)}, supplies={len(supply_df)} ===")

# 核心信息
a_core = {row.core_id: {"speed": row.speed_factor,
                        "scheduler": row.scheduler.strip().upper()} for _, row in arch_df.iterrows()}

# BDR → 供给
a_supply = supply_df.set_index("component_id").to_dict("index")

# --------------------------------------------------
# 构建组件结构
# --------------------------------------------------
components = {}
for _, row in tasks_df.iterrows():
    cid = row.component_id
    if cid not in a_supply:
        print(f"[WARN] {row.task_name} 的 component {cid} 无供给条目，跳过")
        continue
    if cid not in components:
        info = a_supply[cid]
        components[cid] = {
            "core_id"   : info["core_id"],
            "scheduler" : info["scheduler"].upper(),   # 内部
            "Q"         : info["Q"],
            "P"         : info["P"],
            "budget"    : 0.0,
            "priority"  : info.get("priority"),         # 顶层 RM 用
            "tasks"     : []
        }
    speed = a_core[components[cid]["core_id"]]["speed"]
    components[cid]["tasks"].append({
        "name"      : row.task_name,
        "period"    : row.period,
        "wcet"      : row.wcet / speed,   # 再保险
        "priority"  : row.priority,
        # Job runtime state
        "release"   : None,
        "deadline"  : None,
        "remaining" : 0.0,
        "miss_cnt"  : 0,
        "rts"       : []
    })

# 将组件挂到核
cores = {}
for cid, comp in components.items():
    core_id = comp["core_id"]
    cores.setdefault(core_id, {"scheduler": a_core[core_id]["scheduler"], "components": {}})["components"][cid] = comp

# --------------------------------------------------
# 仿真循环
# --------------------------------------------------
print("\n--- 仿真开始 ---")
for t in range(SIM_TIME):
    # 1) 供给补充 & 任务释放
    for comp in components.values():
        if t % comp["P"] == 0:
            comp["budget"] += comp["Q"]
        for task in comp["tasks"]:
            if t % task["period"] == 0:
                task["release"]   = t
                task["deadline"]  = t + task["period"]
                task["remaining"] = task["wcet"]
    # 2) 每核调度组件
    for core in cores.values():
        ready_comps = [c for c in core["components"].values() if c["budget"]>EPS and any(tsk["remaining"]>EPS for tsk in c["tasks"])]
        if not ready_comps:
            continue
        if core["scheduler"] == "RM":
            ready_comps.sort(key=lambda c: c["priority"] if (c.get("priority") is not None and not (isinstance(c.get("priority"), float) and math.isnan(c.get("priority")))) else 1e9)
        else:  # EDF
            ready_comps.sort(key=lambda c: min(tsk["deadline"] for tsk in c["tasks"] if tsk["remaining"]>EPS))
        comp = ready_comps[0]

        # 3) 组件内部选任务
        runnable = [tsk for tsk in comp["tasks"] if tsk["remaining"]>EPS]
        if comp["scheduler"] == "RM":
            runnable.sort(key=lambda tsk: tsk["priority"] if pd.notna(tsk["priority"]) else 1e9)
        else:  # EDF
            runnable.sort(key=lambda tsk: tsk["deadline"])
        task = runnable[0]

        # 4) 执行
        exec_amt = min(task["remaining"], QUANTUM, comp["budget"])
        task["remaining"] -= exec_amt
        comp["budget"]   -= exec_amt

        # 5) 任务完成检查
        if task["remaining"] <= EPS:
            finish_time = t + exec_amt
            rt = finish_time - task["release"]
            task["rts"].append(rt)
            if finish_time > task["deadline"] + EPS:
                task["miss_cnt"] += 1

# 6) 仿真结束后：若仍有剩余执行量视为 miss
for comp in components.values():
    for task in comp["tasks"]:
        if task["remaining"] > EPS:
            task["miss_cnt"] += 1
print("--- 仿真结束 ---\n")

# --------------------------------------------------
# 结果汇总
# --------------------------------------------------
rows = []
for cid, comp in components.items():
    comp_schedulable = all(tsk["miss_cnt"]==0 for tsk in comp["tasks"])
    for task in comp["tasks"]:
        rows.append({
            "task_name"           : task["name"],
            "component_id"        : cid,
            "task_schedulable"    : int(task["miss_cnt"]==0),
            "avg_response_time"   : round(sum(task["rts"])/len(task["rts"],) ,2) if task["rts"] else 0.0,
            "max_response_time"   : max(task["rts"], default=0.0),
            "component_schedulable": int(comp_schedulable)
        })

os.makedirs(os.path.dirname(config.SOLUTION_PATH), exist_ok=True)
pd.DataFrame(rows).to_csv(config.SOLUTION_PATH, index=False)
print(f"✅ 结果已写入 {config.SOLUTION_PATH} (rows={len(rows)})")
