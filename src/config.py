# config.py

import os

# 基本路径配置
BASE_PATH = "/Users/Zayne/DTU/S2/Distributed Real-Time Systems/02225_DRTS/DRTS_Project-Test-Cases/10-unschedulable-test-case"  # 这里可以改成任何数据集文件夹路径

# 输入文件路径
TASKS_PATH = os.path.join(BASE_PATH, "tasks.csv")
ARCH_PATH = os.path.join(BASE_PATH, "architecture.csv")
BUDGETS_PATH = os.path.join(BASE_PATH, "budgets.csv")

# 输出文件路径
OUTPUT_DIR = "/Users/Zayne/DTU/S2/Distributed Real-Time Systems/02225_DRTS/output/10-unschedulable-test-case"  # 输出文件存放的文件夹

# 生成输出文件路径
ANALYSIS_RESULT_PATH = os.path.join(OUTPUT_DIR, "analysis_result.csv")
RESOURCE_SUPPLY_PATH = os.path.join(OUTPUT_DIR, "resource_supply.csv")
SOLUTION_PATH = os.path.join(OUTPUT_DIR, "solution.csv")
PREPROCESSED_TASKS_PATH = os.path.join(OUTPUT_DIR, "preprocessed_tasks.csv")
