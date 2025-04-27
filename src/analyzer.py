import pandas as pd
import math, os
import config
import matplotlib.pyplot as plt


# ---------- Half-Half  α,Δ → Q,P  ----------
def half_half_to_qp(alpha: float, delta: float):
    if alpha >= 1.0:
        raise ValueError("alpha must be < 1")
    if delta == 0:
        P = 100.0
        Q = alpha * P
        return Q, P
    P = delta / (1.0 - alpha)
    Q = alpha * P
    return Q, P



"""下面这段注释不是当前版本的说明，没删是为了大家理解当前版本从哪来的
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
ENABLE_PEAK_INTERFACE_CHECK = True #True=严格峰值检查  False=沿用旧利用率判据
ENABLE_DELAY_PEAK_CHECK = True
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


    #max_period = df_comp["period"].max()
    #max_t = max_period * TEST_HORIZON_FACTOR
    # ---------- 自适应测试时限 ----------
    # 教材依据：《硬实时计算系统》第 4 章 4-3 式提到，用任务超周期能覆盖所有“关键间隔”。
    # 用任务周期的最小公倍数 (hyperperiod) 作为观察窗口上界，
    # 再至少取一倍 Δ_MAX，避免漏掉“错位”间隔。
    # 若 LCM 过大，限定在 10 000。
    from math import lcm
    periods = df_comp["period"].astype(int).tolist()
    try:
        hyper = lcm(*periods)
    except OverflowError:          # 非整数或太大
        hyper = max(periods) * 10
    max_t = min(max(DELTA_MAX * 2, hyper), 10_000)
    test_points = range(1, int(max_t) + 1)


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

    # ------------------------------------------------------------
    # 新：核心 (core) 超载检查
    # ------------------------------------------------------------
    # 对 results 中每条记录，把同一 core 上的 alpha 求和；
    #       只要 Σα > 1.01（给 1% 容差），认为该核心超载。
    #       额外在结果里写两列：
    #         • core_overloaded      -> True / False
    #         • system_schedulable   -> False 若核心超载，否则沿用组件局部 schedulable
    #       这样就能看出“组件都 OK 但系统仍失败”的情况。
    # ------------------------------------------------------------
    # 目的：把同一 core 上所有组件的 α 求和；若 Σα > 1.01 判为超载。
    # 新增两列：
    #     • core_overloaded      True / False  —— 该组件所在核心是否超载
    #     • system_schedulable   True / False  —— 全局视角，可调度 = 组件可调度且核心未超载
    core_load = {}
    for r in results:
        if r["alpha"] is None:  # 组件本身就不可调度 → 视为∞负荷
            core_load[r["core_id"]] = float("inf")
        else:
            core_load[r["core_id"]] = core_load.get(r["core_id"], 0.0) + r["alpha"]

    # 找出 Σα > 1.01 的核心
    overloaded_cores = {cid: load for cid, load in core_load.items() if load > 1.01}

    if overloaded_cores:
        print("\n🚨 系统级检测：以下核心超载 (Σα > 1):")
        for cid, load in overloaded_cores.items():
            print(f"   • {cid}: Σα = {load:.2f}")
    else:
        print("\n✅ 系统级检测：没有核心超载")

    # 把标记写回每条结果
    for r in results:
        r["core_overloaded"] = r["core_id"] in overloaded_cores
        r["system_schedulable"] = (not r["core_overloaded"]) and r["schedulable"]


    # ====== ★ 接口可调度性（Theorem-1）检查 ★ ======
    # 1) 收集每核子接口供应任务 (Q,P) —— 与 sim.py 的公式保持一致
    core_supplies = {}
    for r in results:
        if not r["schedulable"]:
            continue
        try:
            Q, P = half_half_to_qp(r["alpha"], r["delta"])
        except ValueError:
            continue
        core_supplies.setdefault(r["core_id"], []).append((Q, P))

    # 2) 父层 EDF-DBF 可调度性：SBF=t，检查 DBF<=t
    def dbf_periodic(ts, t):
        # return sum(math.floor((t - C) / T + 1) * C if t >= C else 0 for C, T in ts)
        return sum(math.ceil(t / T) * C for C, T in ts) #这样和教材《分布式实时系统…》公式 (2) 保持一致，又远离 “小数 + floor” 的误差陷阱。

    # ---------- 接口可调度性检查 ----------
    def _util_check(core_sup):
        # 旧判据：只看平均利用率
        return {
            core for core, lst in core_sup.items()
            if sum(Q / P for Q, P in lst) > 1.0 + 1e-6
        }

    def _peak_check(core_sup):
        # 新判据：Theorem-1 —— 任一窗口 DBF<=t (父层供给)
        def dbf(lst, t):
            #return sum(math.ceil(t / P) * Q for Q, P in lst)
            return sum(max(0, (math.floor((t - P) / P) + 1)) * Q
                       if t >= P else 0
                       for Q, P in lst)

        unsched = set()
        for core, lst in core_sup.items():
            if not lst:
                continue
            try:
                hp = math.lcm(*[int(P) for _, P in lst])
            except OverflowError:
                hp = max(P for _, P in lst) * 10
            max_t = min(hp, 10_000)
            for t in range(1, max_t + 1):
                if dbf(lst, t) > t + 1e-6:  # 父层 SBF == t
                    unsched.add(core)
                    break
        return unsched

    # --- BDR Δ-delay 峰值检查 ---
    def _delay_check(core_sup):
        """
        Theorem-1 for BDR interfaces:
        Σ α_i·max(0, t−Δ_i) ≤ t   ∀t>0
        α_i = Q/P ,  Δ_i = P−Q
        只需检查临界点 t ∈ {Δ_i}
        """
        unsched = set()
        for core, lst in core_sup.items():
            pairs = [(Q / P, P - Q) for Q, P in lst]
            for t in {int(d) for _, d in pairs} | {0}:
                demand = sum(a * max(0, t - d) for a, d in pairs)
                if demand > t + 1e-6:  # 父层 SBF = t
                    unsched.add(core)
                    break
        return unsched

    if ENABLE_DELAY_PEAK_CHECK:
        interface_unsched = _delay_check(core_supplies)
    elif ENABLE_PEAK_INTERFACE_CHECK:
        interface_unsched = _peak_check(core_supplies)
    else:
        interface_unsched = _util_check(core_supplies)

    if interface_unsched:
        print("\n🚨 接口可调度性失败核心:", ", ".join(interface_unsched))
    else:
        print("\n✅ 接口可调度性全部通过")

    for r in results:
        r["interface_unsched"] = r["core_id"] in interface_unsched
        if r["interface_unsched"]:
            r["system_schedulable"] = False





    # ====== ★ 父接口预算覆盖检查（可迭代）★ ======
    # 前提：budgets.csv 至少含 alpha_budget, delta_budget, component_id 三列
    # ------------------------------------------------
    try:
        budgets_df = pd.read_csv(config.BUDGETS_PATH)

        # ---------- ① 若文件是 (budget, period) 表头，先换算出 alpha_budget, delta_budget ----------
        if {"budget", "period"}.issubset(budgets_df.columns):
            bdg = budgets_df.copy()
            bdg["alpha_budget"] = bdg["budget"] / bdg["period"]
            bdg["delta_budget"] = bdg["period"] - bdg["budget"]
            budgets_df = bdg  # 后续统一使用包含新列的 DataFrame

        # ---------- ② 别名兼容（含刚刚换算出的列） ----------
        alias = {
            "component_id": {"component_id", "comp_id", "cid"},
            "alpha_budget": {"alpha_budget"},
            "delta_budget": {"delta_budget"},
        }
        colmap = {}
        for std, cand in alias.items():
            for col in budgets_df.columns:
                if col.lower() in {x.lower() for x in cand}:
                    colmap[std] = col
                    break

        missing = [std for std in alias if std not in colmap]
        if missing:
            print(f"\n❌ budgets.csv 缺字段 {missing} → 覆盖检查被跳过")
            for r in results:
                r["budget_violate"] = None
            bdg_map = {}
        else:
            # 只保留三列并统一列名
            budgets_df = budgets_df[[colmap["component_id"],
                                     colmap["alpha_budget"],
                                     colmap["delta_budget"]]]
            budgets_df.columns = ["component_id", "alpha_budget", "delta_budget"]
            bdg_map = budgets_df.set_index("component_id")[["alpha_budget", "delta_budget"]].to_dict("index")

            # ---------- ★ 父预算覆盖实际比对 ★ ----------
            violate_any = False
            print("\n🔍 父接口预算覆盖检查")
            for r in results:
                need_a, need_d = r["alpha"], r["delta"]
                cid = r["component_id"]
                if cid not in bdg_map or need_a is None:
                    r["budget_violate"] = None
                    continue
                bud_a = bdg_map[cid]["alpha_budget"]
                bud_d = bdg_map[cid]["delta_budget"]
                violate = (need_a > bud_a + 1e-6) or (need_d > bud_d + 1e-6)
                r["budget_violate"] = violate
                if violate:
                    violate_any = True
                    r["system_schedulable"] = False
                    print(f"   • {cid}: 需求(α={need_a:.2f},Δ={need_d}) > 预算(α={bud_a:.2f},Δ={bud_d}) ❌")

            if not violate_any:
                print("   ✔ 全部子组件需求被父预算覆盖")
            # ---------- ★ 比对结束 ★ ----------





    except FileNotFoundError:
        print("\nℹ️ 未找到 budgets.csv，跳过父预算检查")
        for r in results: r["budget_violate"] = None

    # ====== ★ Case 总体可调度性 ★ ======
    case_schedulable = all(r["system_schedulable"] for r in results)
    print("\n🌟 Case verdict:",
          " SCHEDULABLE ✅" if case_schedulable else "UNSCHEDULABLE ❌")
    for r in results:
        r["case_schedulable"] = case_schedulable



    os.makedirs(os.path.dirname(config.ANALYSIS_RESULT_PATH), exist_ok=True)
    pd.DataFrame(results).to_csv(config.ANALYSIS_RESULT_PATH, index=False)
    print(f"\n✅ 分析完成，结果写入 {config.ANALYSIS_RESULT_PATH}\n")





bud = pd.read_csv(config.BUDGETS_PATH)
print("\n=== budgets.csv columns ===")
print(list(bud.columns))          # ← 真实列名就在这里

if __name__ == "__main__":
    main()
