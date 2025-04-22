# 02225-DRTS


## 1. 项目概述

本项目是一个基于 **实时系统** 的任务调度仿真器，旨在模拟和分析不同调度策略（如 **RM (Rate Monotonic)** 和 **EDF (Earliest Deadline First)**）下的任务调度效果。项目通过分析任务集和调度算法，计算每个任务的 **最坏响应时间**（WCRT）并进行调度验证。最终生成调度方案、任务响应时间等仿真结果。

## 2. 项目要求与完成情况对照

| **项目要求**                                                                 | **完成情况**                                                                                                         |
|----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| **工具开发**：开发一个软件工具计算周期性和偶发性任务的 **最坏响应时间**（WCRT）。                 | 通过 `analyzer.py` 计算任务的最坏响应时间，并验证任务的可调度性。                                           |
| **调度性分析验证**：将分析结果与其他方法（如手动计算、仿真等）进行对比，识别并解释差异。       | 通过二分法搜索最小的 **Q** 值来进行调度验证，模拟任务是否能够在给定的约束下完成。 |
| **详细的结果分析**：记录仿真和分析的结果，明确解释每个结果的意义，特别是在 ADAS 任务调度中的应用。 | 分析了不同调度策略（RM 和 EDF）下的任务调度，生成了响应时间、可调度性等结果并输出为 `solution.csv` 文件。 |
| **比较性能评估**：评估不同调度技术的效果，分析它们对 **WCRT**、错过的截止时间等性能指标的影响。   | 使用二分法自动调整 **Q** 和 **P**，并比较不同调度策略的性能影响。                                          |
| **测试用例**：开发多个真实的系统场景，包括不同的流量、负载、配置参数。                           | 使用多个测试数据集（如 `10-unschedulable-test-case`）进行模拟。                                             |
| **批判性评估**：讨论选择的调度方法的优缺点，提出改进方案或进一步研究的方向。                    | 在 `README.md` 和代码注释中提供了对调度方法的批判性分析。                                                   |
| **团队协作**：展示团队任务分工并整合个人贡献。                                           | 所有文件和功能模块都有明确的职责划分，项目结构清晰。                                                         |
| **报告编写**：报告内容清晰，使用简洁的技术语言，正确引用所有参考文献。                               | 项目的所有细节都有详细的描述，所有功能的实现都在报告中有所体现。                                              |

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
    ├── auto_tuner.py
    ├── config.py
    ├── Drts.py
    ├── sim.py
    └── simulate_full_auto.py
```

### 各目录/文件说明：
- **`/src`**：存放项目的主要代码文件。
  - **`Drts.py`**：负责任务和组件的初始化，加载任务数据并生成预处理任务文件。
  - **`analyzer.py`**：计算任务的最坏响应时间（WCRT），分析任务的调度可调度性。
  - **`sim.py`**：进行自动调优，生成调优后的资源供应文件。
  - **`simulate_full_auto.py`**：进行任务调度仿真，输出调度结果。
  
- **`/config`**：存放配置文件，集中管理路径配置。
  - **`config.py`**：管理任务数据集路径、输出路径等配置。
  
- **`/output`**：存放所有生成的输出文件。
  - **`analysis_result.csv`**：记录任务调度的分析结果。
  - **`resource_supply.csv`**：记录调优后的资源供应数据。
  - **`solution.csv`**：仿真结果，包含响应时间等性能指标。

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


1. **运行顺序**：

- Drts.py：加载任务数据，生成 `preprocessed_tasks.csv` 。
- analyzer.py：读取 `preprocessed_tasks.csv` ，分析任务调度的可调度性，生成 ` analysis_result.csv` 。
- sim.py：根据分析结果进行调参，生成 `resource_supply.csv` 。
- simulate_full_auto.py：执行调度仿真，输出 `solution.csv` 。


## 5. 运行示例

假设你已经设置好路径并完成所有文件配置，运行代码的过程如下：

- 运行 Drts.py，它会生成 `preprocessed_tasks.csv` 。
- 运行 analyzer.py，它会使用 `preprocessed_tasks.csv`  并生成 `analysis_result.csv` 。
- 运行 sim.py，它会基于 `analysis_result.csv` 进行调优并生成 `resource_supply.csv` 。
- 最后，运行 `simulate_full_auto.py` ，它将仿真调度并生成最终的仿真结果 `solution.csv`。
