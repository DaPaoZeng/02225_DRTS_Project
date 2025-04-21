def auto_tune_supply(task_path, arch_path, sched_path, output_path):
    import pandas as pd

    task_df = pd.read_csv(task_path)
    arch_df = pd.read_csv(arch_path)
    sched_df = pd.read_csv(sched_path)

    # 默认所有 component schedulable
    if "component_schedulable" in sched_df.columns:
        sched_map = {row["component_id"]: row["component_schedulable"] for _, row in sched_df.iterrows()}
    else:
        print("⚠️ 警告：未找到 'component_schedulable' 列，默认全部设为可调度（1）")
        sched_map = {row["component_id"]: 1 for _, row in sched_df.iterrows()}

    result = []
    for component_id, group in task_df.groupby("component_id"):
        is_schedulable = sched_map.get(component_id, 1)
        for _, row in group.iterrows():
            period = row["period"]
            wcet = row["wcet"]
            # 安全系数：用 1.2 倍 WCET 做预算初始猜测
            Q = round(float(wcet) * 1.2, 2)
            P = period
            result.append({
                "component_id": component_id,
                "core_id": 0,
                "Q": Q,
                "P": P,
                "scheduler": "EDF" if is_schedulable else "RM"
            })

    pd.DataFrame(result).to_csv(output_path, index=False)
    print(f"✅ 自动供给文件已保存：{output_path}")
