import pandas as pd
import math

# === 读取预处理任务文件 ===
df = pd.read_csv("output/preprocessed_tasks.csv")

# === 定义 DBF（RM 版本） ===
def dbf_rm(taskset, t, task_index):
    task_i = taskset[task_index]
    dbf = task_i["wcet"]
    for j in range(task_index):
        hp_task = taskset[j]
        dbf += math.ceil(t / hp_task["period"]) * hp_task["wcet"]
    return dbf

# === 定义 DBF（EDF 版本） ===
def dbf_edf(taskset, t):
    return sum((t // task["period"]) * task["wcet"] for task in taskset)

# === 定义 SBF 函数 ===
def sbf(alpha, delta, t):
    return 0 if t < delta else alpha * (t - delta)

# === 分析器核心函数 ===
def analyze_schedulability(tasks, scheduler, max_t):
    for delta in range(0, 101):
        for a in range(1, 201):  # α from 0.01 to 2.00
            alpha = a / 100
            ok = True

            for t in range(1, max_t + 1):
                if scheduler == "RM":
                    for i in range(len(tasks)):
                        dbf = dbf_rm(tasks, t, i)
                        if dbf > sbf(alpha, delta, t):
                            ok = False
                            break
                elif scheduler == "EDF":
                    dbf = dbf_edf(tasks, t)
                    if dbf > sbf(alpha, delta, t):
                        ok = False

                if not ok:
                    break
            if ok:
                return True, round(alpha, 2), delta
    return False, None, None

# === 分析每个组件 ===
grouped = df.groupby("component_id")
results = []

for comp_id, group in grouped:
    print(f"\n分析组件：{comp_id}")
    original_scheduler = group["scheduler"].iloc[0].strip().upper()
    core_id = group["core_id"].iloc[0]

    tasks = group.sort_values("priority").to_dict("records")
    max_t = max([task["period"] for task in tasks]) * 5

    # 默认用原始 scheduler 分析
    feasible, best_alpha, best_delta = analyze_schedulability(tasks, original_scheduler, max_t)
    final_scheduler = original_scheduler

    # 如果 RM 不可调度，自动尝试 EDF
    if not feasible and original_scheduler == "RM":
        print(f"⚠️  {comp_id} 在 RM 下不可调度，尝试使用 EDF...")
        feasible, best_alpha, best_delta = analyze_schedulability(tasks, "EDF", max_t)
        if feasible:
            final_scheduler = "EDF (fallback)"

    results.append({
        "component_id": comp_id,
        "core_id": core_id,
        "scheduler": final_scheduler,
        "alpha": best_alpha,
        "delta": best_delta,
        "schedulable": feasible
    })

# === 输出分析结果 ===
output_df = pd.DataFrame(results)
output_df.to_csv("output/analysis_result.csv", index=False)
print("\n✅ 分析完成，结果保存在 analysis_result.csv")
