# 农产品价格波动对中国GDP的影响研究（analyse.pjhaapy）

本项目聚焦“农产品价格波动与中国宏观（第一产业权重GDP）”之间的弹性关系，构建了一套从数据处理到可视化与可解释结果的轻量级分析流水线，支持可复现、可溯源的研究与展示。

## 项目目标
- 建立在对数差分（ΔLog）的波动度量基础上，量化“价格—宏观”的相关性与滞后效应。
- 通过平滑（EWMA）与预白化冲击（创新项）等处理，提升信号质量与统计稳健性。
- 用直观图表呈现“最佳方法×最佳滞后”的结果与“滞后全貌”，为后续建模与论证提供依据。

## 数据与血缘
- 原始/中间数据（CSV/JSON 等）位于仓库根目录（如 `START_*.csv`、`START_top_predictors.json` 等）。
- 可视化依赖的前端数据文件：`start_echarts_data.js`（由数据构建脚本生成，供前端直接引用）。
- 主要脚本（Python）：
  - `build_start.py`：读取原始数据，计算相关与滞后结果，生成前端数据文件与统计表。
  - `check_lags.py`：滞后期相关性检查与显著性检验。
  - `build_model_data.py`：特征工程与建模数据集构建（可按需使用）。

> 说明：脚本的第三方依赖（如 `pandas`、`numpy`、`statsmodels` 等）请按环境安装；建议 Python 3.9+。

## 方法与口径
- 波动度量：对数差分 ΔLog，增强平稳性与可比性。
- 平滑与冲击：
  - EWMA：指数加权移动平均，降低短期噪声。
  - 预白化冲击：去除自相关后的“创新项”，提升相关分析时的信号纯度。
- 滞后定义：比较 `r[ΔLog(权重GDP)_t, X_{t−k}]`，系统评估不同商品在不同滞后期的相关。
- 显著性与标注：在图表中显示 p 值星标（`*` 表示 p≤0.05，`**` 表示 p≤0.01），并在 tooltip 中给出精确 p 值。

## 可视化与阅读路径
前端入口：`show.html`（直接双击或在浏览器打开）。可视化由 [ECharts](https://echarts.apache.org/) 驱动，读取 `start_echarts_data.js`。

在线预览（渲染版）：
- https://raw.githack.com/pjhappy-1999/analyse.pjhaapy/main/show.html

说明：GitHub 仓库页面点开 `show.html` 默认展示的是源码；通过上述链接可直接渲染展示页面效果。

核心版块（已精简聚焦在“基础数据处理 + 滞后性”的结论与过程）：
1. 原始数据概览：时间序列对齐，便于直观观察趋势。
2. 相关性分析：GDP 水平/Log 弹性的热力图与表格。
3. 波动率与滞后弹性（基础数据处理）：
   - 合并终图（Best-Lag Summary Bar）：逐商品给出“优先显著且 |r| 最大”的最佳方法×最佳滞后结果。
   - 最佳热力图（Best Heatmap）：与合并终图口径一致的矩阵视图，统一展示各商品最佳 r。
   - EWMA 滞后热力图（Lag Heatmap）：展示 0–5 阶滞后全貌，并标注显著性星标。
   - 小字说明：简要说明 ΔLog、EWMA、预白化与滞后口径；详细推导放在脚本侧实现。

阅读建议：先看“合并终图/最佳热力图”把握主结论，再看“滞后热力图”理解相关性提升来源（滞后结构）。

## 快速开始
1. 直接查看可视化  
   - 打开 `show.html`（需与 `start_echarts_data.js` 位于同一目录）。
2. 重新生成前端数据（可选）  
   - 安装 Python 依赖（按需）：`pip install pandas numpy statsmodels`  
   - 运行脚本：`python build_start.py`  
   - 生成的 `start_echarts_data.js` 会覆盖可视化所用的数据。

## 仓库结构（节选）
- `show.html`：前端页面（ECharts 可视化）。
- `start_echarts_data.js`：可视化数据（由脚本生成）。
- `build_start.py` / `check_lags.py` / `build_model_data.py`：数据处理与统计分析脚本。
- `START_*.csv`：中间/输出数据集，用于溯源与验证。

## 版本管理与溯源
- Git 主分支：`main`，远程仓库：`origin`  
  `https://github.com/pjhappy-1999/analyse.pjhaapy.git`
- 任意改动请：
  - 更新脚本或数据 → 运行生成 → 校验可视化 → 提交并推送：
    ```bash
    git add .
    git commit -m "feat: 更新数据与可视化（示例）"
    git push
    ```

## 路线图（可选）
- 增加方法切换控件（原始ΔLog / EWMA / 预白化）与显著筛选/排序开关。
- 将 EWMA 参数、滞后阶数等暴露为可配置项，支持不同场景的稳健性检验。
- 引入更加系统的分布式滞后回归（DL/ARDL）对比与可视化。

---
如需增补数据字段说明、脚本参数或学术写作版图表注释，请开 Issue 或直接标注需求，我将持续补全。 
