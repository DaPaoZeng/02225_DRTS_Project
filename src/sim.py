import pandas as pd
import math, os
import config

"""sim.py  —  Half‑Half 转换 (verbose)
--------------------------------------------------
读取 analyzer 的 α,Δ 结果 → 生成 resource_supply.csv (Q,P)
注意：此文件只负责转换，不做仿真。
"""

# --------------------------------------------------
# Helper: Half‑Half theorem
# --------------------------------------------------

def half_half_to_qp(alpha: float, delta: float):
    """Given BDR (α,Δ) 返回供给任务 (Q,P)。
    Theorem 3:  P = Δ / (1‑α)   Q = α·P   (隐式 P>0, α<1)。
    若 Δ==0 视为固定带宽，返回 P=hyperperiod_like = 100, Q=α·P。
    """
    if alpha >= 1.0:
        raise ValueError("alpha must be < 1 for Half‑Half")
    if delta == 0:
        P = 100.0  # 可根据需要改为其他常数或最大 period
        Q = alpha * P
        return round(Q, 2), round(P, 2)
    P = delta / (1.0 - alpha)
    Q = alpha * P
    return round(Q, 2), round(P, 2)

# --------------------------------------------------
# Main
# --------------------------------------------------

def main():
    analysis_path = config.ANALYSIS_RESULT_PATH
    out_path = config.RESOURCE_SUPPLY_PATH

    df = pd.read_csv(analysis_path)
    print(f"=== Half‑Half 转换：读取 {analysis_path} 共 {len(df)} 行 ===")
    task_df = pd.read_csv(config.PREPROCESSED_TASKS_PATH) #加载任务表

    rows = []
    for idx, row in df.iterrows():
        comp_id = row["component_id"]
        alpha = row["alpha"]
        delta = row["delta"]
        #计算当前组件负载：报告中展示任务总负载与α的对比，判断α是否过度保守或紧张，可辅助判断 α 合理性
        df_tasks = task_df[task_df["component_id"] == comp_id]
        load = sum(df_tasks["wcet"] / df_tasks["period"])
        load = round(load, 3)

        schedulable = bool(row["schedulable"])
        scheduler = row["scheduler"].strip().upper()
        core_id = row["core_id"]

        if not schedulable or pd.isna(alpha) or pd.isna(delta):
            print(f"[SKIP] {comp_id} 不可调度或缺少 αΔ")
            continue
        if alpha >= 1.0:
            print(f"[WARN] {comp_id} α≥1.0 (={alpha})，无法用 Half‑Half")
            continue
        try:
            Q, P = half_half_to_qp(alpha, delta)
            rows.append({
                "component_id": comp_id,
                "core_id": core_id,
                "scheduler": scheduler,
                "Q": Q,
                "P": P,
                "load": load
            })
            print(f"[OK] {comp_id:<15} α={alpha:<4} Δ={delta:<3} ⇒ Q={Q:<6} P={P:<6}  load={load}")
        except ValueError as e:
            print(f"[ERR] {comp_id}: {e}")

    if not rows:
        print("✗ 未生成任何供给任务！")
        return

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pd.DataFrame(rows).to_csv(out_path, index=False)
    print(f"\n✅ resource_supply.csv 写入 {out_path} (rows={len(rows)})")

if __name__ == "__main__":
    main()

"""
# | 变动 | 原因
1 | 正确 Half-Half 公式 P = Δ / (1-α), Q = α·P | 纠正旧版 P = Δ / (2·(1-α)) + safety factor 的错误
2 | 当 Δ == 0 视为固定带宽：P = 100, Q = α·P | 保证 α>0 情况仍能生成供给任务
3 | 去掉 Camera_Sensor 硬编码特判 & safety_factor | 保持通用性
4 | 详细日志  • 读入/行数  • 每组件 α,Δ→Q,P  • 跳过/警告/错误打印 | 运行时可一目了然转换流程
5 | 生成目录不存在时自动创建 | 兼容 CI/新机器
6 | 输入字段统一 upper() | 防止大小写混用影响后续

"""