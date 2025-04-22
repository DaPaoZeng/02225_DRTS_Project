
import pandas as pd
import numpy as np
import os
import config  # 导入配置文件

# === 参数路径 ===
TASKS_PATH = config.TASKS_PATH
ARCH_PATH = config.ARCH_PATH
ANALYSIS_PATH = config.ANALYSIS_RESULT_PATH
OUTPUT_PATH = config.SOLUTION_PATH
SIM_TIME = 5000
P_FIXED = 130.0

# === 加载数据 ===
tasks_df = pd.read_csv(TASKS_PATH)
arch_df = pd.read_csv(ARCH_PATH)
analysis_df = pd.read_csv(ANALYSIS_PATH)

core_speed = dict(zip(arch_df["core_id"], arch_df["speed_factor"]))
core_list = arch_df["core_id"].tolist()

# === 自动调参：最小可调度 Q 搜索 ===
supply_map = {}
grouped_tasks = dict(tuple(tasks_df.groupby("component_id")))

for i, (_, row) in enumerate(analysis_df.iterrows()):
    comp_id = row["component_id"]
    core_id = row["core_id"]
    scheduler = row["scheduler"].strip().upper()
    if "EDF" in scheduler:
        scheduler = "EDF"
    elif "RM" in scheduler:
        scheduler = "RM"
    else:
        scheduler = "EDF"

    if comp_id not in grouped_tasks or core_id not in core_speed:
        continue

    group = grouped_tasks[comp_id]
    speed = core_speed[core_id]

    def simulate(Q):
        task_pool = []
        supply_budget = 0.0
        for t in range(SIM_TIME):
            if t % P_FIXED == 0:
                supply_budget += Q
            for _, task in group.iterrows():
                if t % task["period"] == 0:
                    task_pool.append({
                        "name": task["task_name"],
                        "remaining": float(task["wcet"]) / speed,
                        "release": t,
                        "deadline": t + task["period"],
                        "priority": task["priority"]
                    })
            while supply_budget >= 1.0 and task_pool:
                if scheduler == "RM":
                    task_pool.sort(key=lambda x: x["priority"])
                elif scheduler == "EDF":
                    task_pool.sort(key=lambda x: x["deadline"])
                else:
                    task_pool.sort(key=lambda x: x["release"])
                current = task_pool[0]
                exec_amount = min(current["remaining"], 1.0)
                current["remaining"] -= exec_amount
                supply_budget -= exec_amount
                if current["remaining"] <= 0.0001:
                    task_pool.pop(0)
                else:
                    break
        return not any(task["deadline"] < SIM_TIME for task in task_pool)

    # 二分搜索最小 Q
    low, high = 5.0, 130.0
    best_q = None
    while high - low > 0.1:
        mid = round((low + high) / 2, 2)
        if simulate(mid):
            best_q = mid
            high = mid
        else:
            low = mid

    if best_q:
        supply_map[comp_id] = {
            "Q": round(best_q, 2),
            "P": P_FIXED,
            "core_id": core_id,
            "scheduler": scheduler
        }

# === 仿真部分 ===
results = []
for comp_id, group in tasks_df.groupby("component_id"):
    if comp_id not in supply_map:
        continue
    supply = supply_map[comp_id]
    Q = supply["Q"]
    P = supply["P"]
    core_id = supply["core_id"]
    scheduler = supply["scheduler"]
    speed = core_speed[core_id]

    task_pool = []
    supply_budget = 0.0
    response_times = {name: [] for name in group["task_name"]}

    for t in range(SIM_TIME):
        if t % P == 0:
            supply_budget += Q

        for _, task in group.iterrows():
            if t % task["period"] == 0:
                task_pool.append({
                    "name": task["task_name"],
                    "remaining": float(task["wcet"]) / speed,
                    "release": t,
                    "deadline": t + task["period"],
                    "priority": task["priority"]
                })

        while supply_budget >= 1.0 and task_pool:
            if scheduler == "RM":
                task_pool.sort(key=lambda x: x["priority"])
            elif scheduler == "EDF":
                task_pool.sort(key=lambda x: x["deadline"])
            else:
                task_pool.sort(key=lambda x: x["release"])

            current = task_pool[0]
            exec_amount = min(current["remaining"], 1.0)
            current["remaining"] -= exec_amount
            supply_budget -= exec_amount

            if current["remaining"] <= 0.0001:
                rt = t - current["release"] + 1
                response_times[current["name"]].append(rt)
                task_pool.pop(0)
            else:
                break

    missed = any(task["deadline"] < SIM_TIME for task in task_pool)
    max_rt = max([max(r) if r else 0 for r in response_times.values()])
    avg_rt = round(sum([x for v in response_times.values() for x in v]) / max(1, sum(len(v) for v in response_times.values())), 2)

    results.append({
        "component_id": comp_id,
        "core_id": core_id,
        "scheduler": scheduler,
        "schedulable": not missed,
        "max_response_time": max_rt,
        "avg_response_time": avg_rt
    })

pd.DataFrame(results).to_csv(OUTPUT_PATH, index=False)
print(f"✅ simulate_full_auto 完成，结果已保存：{OUTPUT_PATH}")
