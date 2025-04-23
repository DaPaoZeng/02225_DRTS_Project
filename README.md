# 02225-DRTS


## 1  项目概述
本仓库实现了一个 **分层实时系统任务调度仿真器**，可在多核平台上比较 **RM (Rate Monotonic)** 与 **EDF (Earliest Deadline First)** 等策略的效果。  
工具链涵盖 **分析-调参-仿真-自动验收** 四个阶段，并输出最坏响应时间 (WCRT)、服务器参数 (Q,P)、以及逐 job 的完成/超时信息。



## 2  项目要求与完成情况

| 项目要求 | 已实现 |
|----------|--------|
| **工具开发**：计算周期/偶发任务的 WCRT | `analyzer.py` 解析 DBF/SBF，标出组件可调度区间 |
| **调度性验证**：与仿真比对 | `check_solution.py` 自动判断是否仍有 deadline-miss |
| **结果分析**：解释 ADAS 场景意义 | README & 代码注释阐述 α/Δ 与 (Q,P) 的物理含义 |
| **性能评估**：对比 RM vs EDF | 切换 `task_sched` 字段即可，统计 miss / lateness |
| **多用例**：不同负载、配置 | 1-10 官方 case 全覆盖，含 4 个不可调场景 |
| **批判性评估** | README 第 6 章列出局限与改进 |
| **团队协作 & 报告** | 文件头 `__author__` 标注职责，另附 `report.pdf` |

---


## 3. 目录结构
```bash
02225_DRTS
├── DRTS_Project-Test-Cases/
│   ├── 1-tiny-test-case
│   ├── 2-small-test-case
│   ├── 3-medium-test-case
│   ├── 4-large-test-case
│   ├── 5-huge-test-case
│   ├── 6-gigantic-test-case
│   ├── 7-unschedulable-test-case
│   ├── 8-unschedulable-test-case
│   ├── 9-unschedulable-test-case
│   ├── 10-unschedulable-test-case/
│   │   ├── architecture.csv
│   │   ├── budgets.csv
│   │   └── tasks.csv
│   └── README.md
├── output/
│   ├── analysis_result.csv       # 记录任务调度的分析结果
│   ├── resource_supply.csv       # 记录调优后的资源供应数据
│   └── solution.csv             # 记录最终解决方案数据
└── src/
    ├── analyzer.py
    ├── solution_check.py
    ├── config.py
    ├── Drts.py
    ├── sim.py
    └── simulate_full_auto.py
```

### 各目录 / 文件说明

- **`/src`**：项目主代码  
  | 文件 | 作用 |
  |------|------|
  | **`Drts.py`** | 读取 *tasks / architecture / budgets*，完成任务与组件初始化并导出 `preprocessed_tasks.csv` |
  | **`analyzer.py`** | 计算 WCRT，搜索组件级接口参数 (α, Δ)，输出 `analysis_result.csv` |
  | **`sim.py`** | 依据 Half-Half 定理把 (α, Δ) → 服务器参数 (Q,P)，生成 `resource_supply.csv` |
  | **`simulate_full_auto.py`** | 结合任务、服务器供给、核心分配进行完整离线仿真，生成 `solution.csv` |
  | **`check_solution.py`** | 快速校验 `solution.csv` 是否存在 deadline miss，并给出统计摘要 |
  | **`config.py`** | 统一配置（数据集路径、输出目录等），一处修改全流程生效 |

- **`/config`**：同上，当前仅含 `config.py`（已在表中列出）。

- **`/output`**：按测试用例自动分子目录保存所有结果  
  | 文件 | 说明 |
  |------|------|
  | `preprocessed_tasks.csv` | Drts 预处理后的展平任务列表 |
  | `analysis_result.csv` | 组件级分析结果：α、Δ、可调度标志等 |
  | `resource_supply.csv` | Half-Half 转换后的服务器供给表 (Q,P) |
  | `solution.csv` | 仿真 Job-trace：avg/max 响应时间、miss 标志等 |

> 若后续新增或删减脚本，只需在此表补充 / 删除对应行即可。


## 4. 代码使用说明

### 如何运行代码：

1. **修改路径配置**：
   - 打开 `config/config.py` 文件。
   - 根据自己的项目目录结构，修改以下路径为绝对路径：
   
   ```python
   # config.py

   import os

   BASE_PATH = "/Users/Zayne/DTU/S2/Distributed Real-Time Systems/02225_DRTS/DRTS_Project-Test-Cases/9-unschedulable-test-case"  # 数据集路径
   TASKS_PATH = os.path.join(BASE_PATH, "tasks.csv")
   ARCH_PATH = os.path.join(BASE_PATH, "architecture.csv")
   BUDGETS_PATH = os.path.join(BASE_PATH, "budgets.csv")

   OUTPUT_DIR = "/Users/Zayne/DTU/S2/Distributed Real-Time Systems/02225_DRTS/output/9-unschedulable-test-case"  # 输出路径

   ANALYSIS_RESULT_PATH = os.path.join(OUTPUT_DIR, "analysis_result.csv")
   RESOURCE_SUPPLY_PATH = os.path.join(OUTPUT_DIR, "resource_supply.csv")
   SOLUTION_PATH = os.path.join(OUTPUT_DIR, "solution.csv")
   PREPROCESSED_TASKS_PATH = os.path.join(OUTPUT_DIR, "preprocessed_tasks.csv")


### 运行顺序（4 步即可）

1. **`Drts.py`**  
   读取 *tasks / architecture / budgets* → 生成 **`preprocessed_tasks.csv`**

2. **`analyzer.py`**  
   读取 `preprocessed_tasks.csv` → 计算每个组件的 (α, Δ) 与可调度性 → 输出 **`analysis_result.csv`**

3. **`sim.py`**  
   把 (α, Δ) 按 *Half-Half* 定理转换为服务器参数 (Q,P) → 输出 **`resource_supply.csv`**

4. **`simulate_full_auto.py`**  
   综合任务、服务器供给和核心映射执行离线仿真 → 生成 **`solution.csv`**

> 可选：运行 **`check_solution.py`** 对 `solution.csv` 做一键验证，快速查看有无 deadline-miss。

---

## 5. 运行示例

直接运行main文件将批量运行10个示例。

```bash
# Step-1 预处理
python src/Drts.py
#  → output/.../preprocessed_tasks.csv

# Step-2 组件级分析
python src/analyzer.py
#  → output/.../analysis_result.csv

# Step-3 Half-Half 转换
python src/sim.py
#  → output/.../resource_supply.csv

# Step-4 完整仿真
python src/simulate_full_auto.py
#  → output/.../solution.csv

# (可选) Step-5 快速检查
python src/check_solution.py
