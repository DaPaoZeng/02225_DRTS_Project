import pandas as pd
import math, os
import config
import matplotlib.pyplot as plt

"""analyzer.py — 组件级 α,Δ 搜索 (Verbose, RM‑DBF 修正版)
--------------------------------------------------
1. **EDF** 采用 Eq.(2)/(3) 计算 `dbf_edf`。
2. **RM/FPS** 采用 Eq.(4) — 先按优先级排序，再对每个任务求 `dbf_i(t)`，取最大。
3. 搜索 Δ∈[0,200]，对每 Δ 求最小 α = max_t (dbf/(t‑Δ))。
4. 打印组件明细、首次可行 Δ、最终 α,Δ。
"""
# --------------------------------------------------
# 图像输出目录
# --------------------------------------------------
PLOT_OUTPUT_DIR = os.path.join(config.OUTPUT_DIR, "plots") #为每个组件生成 dbf vs sbf 折线图

# --------------------------------------------------
# 参数
# --------------------------------------------------
DELTA_MAX = 200
ALPHA_GRAN = 0.01
TEST_HORIZON_FACTOR = 5

# --------------------------------------------------
# 通用 DBF 帮助函数
# --------------------------------------------------

def n_jobs_implicit_deadline(t: int, T: float) -> int:
    """返回在区间 [0,t) 内任务产生的 job 数 (implicit deadline)。"""
    if t < T:
        return 0
    return math.floor((t - T) / T) + 1


def dbf_edf(tasks, t):
    return sum(n_jobs_implicit_deadline(t, T) * C for C, T in tasks)


def dbf_rm(tasks_sorted_by_priority, t):
    """tasks 已按 RM 优先级从高到低排序。返回 max_i dbf_i(t)。"""
    worst = 0.0
    for idx in range(len(tasks_sorted_by_priority)):
        demand = 0.0
        for j in range(idx + 1):  # high‑or‑equal priority (自任务含在内)
            C_j, T_j = tasks_sorted_by_priority[j]
            demand += n_jobs_implicit_deadline(t, T_j) * C_j
        worst = max(worst, demand)
    return worst

# --------------------------------------------------
# 逐组件分析
# --------------------------------------------------

def analyze_component(df_comp: pd.DataFrame):
    comp_id = df_comp["component_id"].iloc[0]
    scheduler = df_comp["scheduler"].iloc[0].strip().upper()

    # RM 任务需按优先级排序（priority 列数值越小优先级越高）
    if scheduler == "RM":
        df_comp = df_comp.sort_values("priority")
    tasks = list(zip(df_comp["wcet"], df_comp["period"]))

    max_period = df_comp["period"].max()
    max_t = max_period * TEST_HORIZON_FACTOR
    test_points = range(1, int(max_t) + 1)

    print(f"\n[COMP] {comp_id}  sched={scheduler}  tasks={len(tasks)}  max_t={max_t}")
    for idx, (C, T) in enumerate(tasks, 1):
        print(f"       └─ Task{idx}: C={C}, T={T}")

    best = None  # (Δ,α)
    for delta in range(DELTA_MAX + 1):
        worst_ratio = 0.0
        feasible = True
        for t in test_points:
            if t <= delta:
                continue
            if scheduler == "EDF":
                demand = dbf_edf(tasks, t)
            else:  # RM
                demand = dbf_rm(tasks, t)
            ratio = demand / (t - delta)
            if ratio > 1.0:
                feasible = False
                break
            worst_ratio = max(worst_ratio, ratio)
        if feasible:
            # alpha = round(math.ceil(worst_ratio / ALPHA_GRAN) * ALPHA_GRAN, 2)
            alpha = round((math.ceil(worst_ratio / ALPHA_GRAN) * ALPHA_GRAN) + 1e-9, 2)
            if alpha > 1.0:
                continue
            print(f"       ✓ first feasible at Δ={delta}, α={alpha}")
            if best is None or delta < best[0] or (delta == best[0] and alpha < best[1]):
                best = (delta, alpha)
    if best:
        print(f"       → chosen Δ={best[0]}, α={best[1]}")
        return True, best[1], best[0]
    print("       ✗ UNSCHEDULABLE within search bounds")
    return False, None, None


# --------------------------------------------------
# dbf vs sbf 折线图
# --------------------------------------------------
def plot_dbf_vs_sbf(comp_id, scheduler, tasks, alpha, delta, max_t):
    ts = list(range(1, int(max_t) + 1))
    dbfs, sbfs = [], []

    for t in ts:
        if scheduler == "EDF":
            dbf = dbf_edf(tasks, t)
        else:
            dbf = dbf_rm(tasks, t)
        dbfs.append(dbf)
        sbfs.append(max(0, alpha * (t - delta)) if t > delta else 0)

    plt.figure()
    plt.plot(ts, dbfs, label="DBF", linewidth=2)
    plt.plot(ts, sbfs, label="SBF", linestyle="--", linewidth=2)
    plt.xlabel("Time (t)")
    plt.ylabel("Resource Demand / Supply")
    plt.title(f"{comp_id} ({scheduler})")
    plt.legend()
    plt.grid(True)

    os.makedirs(PLOT_OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(PLOT_OUTPUT_DIR, f"{comp_id}_dbf_vs_sbf.png")
    plt.savefig(out_path)
    plt.close()
    print(f"       📊 Plot saved to {out_path}")

# --------------------------------------------------
# 主程
# --------------------------------------------------

def main():
    df = pd.read_csv(config.PREPROCESSED_TASKS_PATH)
    print(f"=== Analyzer 启动：读取 {len(df)} task‑rows ===")

    results = []
    for comp_id, group in df.groupby("component_id"):
        ok, alpha, delta = analyze_component(group)
        if ok:
            scheduler = group["scheduler"].iloc[0].strip().upper()
            tasks = list(zip(group["wcet"], group["period"]))
            max_period = group["period"].max()
            max_t = max_period * TEST_HORIZON_FACTOR
            plot_dbf_vs_sbf(comp_id, scheduler, tasks, alpha, delta, max_t)
        results.append({
            "component_id": comp_id,
            "core_id": group["core_id"].iloc[0],
            "scheduler": group["scheduler"].iloc[0].strip().upper(),
            "alpha": alpha,
            "delta": delta,
            "schedulable": ok,
        })

    os.makedirs(os.path.dirname(config.ANALYSIS_RESULT_PATH), exist_ok=True)
    pd.DataFrame(results).to_csv(config.ANALYSIS_RESULT_PATH, index=False)
    print(f"\n✅ 分析完成，结果写入 {config.ANALYSIS_RESULT_PATH}\n")

if __name__ == "__main__":
    main()
