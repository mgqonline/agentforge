---
name: safe_data_processor
description: 当用户要求处理大数据文件（如 CSV, JSON, 日志）、编写数据处理脚本、或执行包含文件读写、网络请求等有潜在风险的代码时，自动触发此技能。
---

# Safe Data Processor & Risk Management

当处理大数据或编写可能带有副作用的代码时，你必须严格遵守以下准则：

## 一、 代码执行风险约束
1. **静态扫描先行**：在执行包含 Python 代码的脚本前，或者编写可能带有副作用的操作时，你可以调用 `scripts/risk_checker.py` 来扫描要执行的脚本文件。
   - 使用方法: `python /Users/mac/Documents/project/ailearning/.agents/skills/safe_data_processor/scripts/risk_checker.py <your_script.py>`
2. **明确副作用**：如果发现告警，在执行前必须向用户预警并请求确认。
3. **只读优先**：所有文件操作必须优先使用只读模式，或者写入到临时/新文件中，禁止直接覆盖源数据。

## 二、 大数据文件处理约束
1. **禁止全量加载**：当处理大文件时，不要使用 `.read()` 全量读入内存。
2. **预览先行**：在进行复杂的数据分析前，请先调用 `scripts/data_chunker.py` 提取表头和前几行数据，确认数据结构。
   - 使用方法: `python /Users/mac/Documents/project/ailearning/.agents/skills/safe_data_processor/scripts/data_chunker.py preview <your_data.csv>`
