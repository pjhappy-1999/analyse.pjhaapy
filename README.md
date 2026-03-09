# 农产品价格波动对中国GDP的影响研究（analyse.pjhaapy）

[![在线预览 show.html](https://img.shields.io/badge/在线预览-show.html-1f6feb)](https://raw.githack.com/pjhappy-1999/analyse.pjhaapy/main/show.html)

本项目聚焦“农产品价格波动与中国宏观（第一产业权重GDP）”之间的弹性关系，构建了一套从数据处理到可视化与可解释结果的轻量级分析流水线，支持可复现、可溯源的研究与展示。

## 项目目标
- 建立在对数差分（ΔLog）的波动度量基础上，量化“价格—宏观”的相关性与滞后效应。
- 通过平滑（EWMA）与预白化冲击（创新项）等处理，提升信号质量与统计稳健性。
- 用直观图表呈现“最佳方法×最佳滞后”的结果与“滞后全貌”，为后续建模与论证提供依据。
- **新增**：深入分析主要农作物（小麦、玉米、大豆、棉花、棕榈油）及原油的季度价格波动率，并探究其对GDP增长的滞后影响。

## 数据与血缘
- 原始/中间数据（CSV/JSON 等）位于仓库根目录（如 `START_*.csv`、`Global WFP Food Prices.csv` 等）。
- 可视化依赖的前端数据文件：
  - `start_echarts_data.js`：基础相关性分析数据。
  - `volatility_gdp_data.js`：**新增**，包含5种作物及原油的季度波动率与GDP数据。
  - `volatility_lag_data.js`：**新增**，包含波动率与GDP增长的滞后相关性分析结果。
- 主要脚本（Python）：
  - `build_start.py`：读取原始数据，计算相关与滞后结果，生成前端数据文件与统计表。
  - `calc_wfp_volatility.py`：**新增**，基于WFP日度价格数据，计算各作物的季度波动率（标准差），并统一货币单位为USD。
  - `calc_lag_analysis.py`：**新增**，计算波动率与GDP增长率在0-8个季度滞后期的相关系数，识别最佳滞后期。
  - `check_lags.py`：滞后期相关性检查与显著性检验。
  - `build_model_data.py`：特征工程与建模数据集构建。

> 说明：脚本的第三方依赖（如 `pandas`、`numpy`、`statsmodels` 等）请按环境安装；建议 Python 3.9+。

## 方法与口径
- **波动度量**：
  - 对数差分 ΔLog：增强平稳性与可比性。
  - 季度波动率：基于日度价格的对数收益率计算季度标准差，衡量价格不确定性。
- **滞后分析**：
  - 范围：考察 0 至 8 个季度的滞后影响。
  - 最佳滞后：选取相关系数绝对值最大且显著（p<0.05）的滞后期作为最佳传导时间。
- **平滑与冲击**：
  - EWMA：指数加权移动平均，降低短期噪声。
  - 预白化冲击：去除自相关后的“创新项”，提升相关分析时的信号纯度。

## 可视化与阅读路径
前端入口：`show.html`（直接双击或在浏览器打开）。可视化由 [ECharts](https://echarts.apache.org/) 驱动。

### 在线预览（渲染版）：
- https://raw.githack.com/pjhappy-1999/analyse.pjhaapy/main/show.html

> 说明：GitHub 仓库页面点开 `show.html` 默认展示的是源码；通过上述链接可直接渲染展示页面效果。

### 核心版块更新：
1. **交互式波动率趋势图**（新增）：
   - **交互控件**：引入磨砂玻璃质感的“球体选择器”，支持在“原油”、“小麦”、“玉米”、“大豆”、“棉花”、“棕榈油”之间快速切换。
   - **双轴展示**：左轴展示选定商品的季度波动率，右轴展示第一产业权重GDP，直观对比波动趋势。
   - **视觉优化**：各作物分配专属主题色，图表线条轻量化处理，支持缩放查看细节。

2. **波动率滞后相关性分析**（新增）：
   - **折线图**：展示各作物在不同滞后期（Lag 0-8）与GDP增长的相关系数变化趋势。
   - **分析汇总**：自动提取每种作物的最佳滞后季度、相关系数及影响方向（正向/负向），并以表格形式呈现。

3. **基础相关性分析**（原有）：
   - 原始数据概览、GDP水平/Log弹性热力图、EWMA滞后热力图等。

## 快速开始
1. 直接查看可视化  
   - 打开 `show.html`（需与 `.js` 数据文件位于同一目录）。
2. 重新生成数据（可选）  
   - 安装依赖：`pip install pandas numpy statsmodels`
   - 运行波动率计算：`python calc_wfp_volatility.py`
   - 运行滞后分析：`python calc_lag_analysis.py`
   - 运行基础分析：`python build_start.py`

## 仓库结构（节选）
- `show.html`：前端页面（集成所有可视化图表）。
- `volatility_gdp_data.js` / `volatility_lag_data.js`：**新增**，波动率相关可视化数据。
- `calc_wfp_volatility.py` / `calc_lag_analysis.py`：**新增**，核心计算脚本。
- `Global WFP Food Prices.csv`：**新增**，WFP全球粮食价格源数据。
- `start_echarts_data.js`：基础分析数据。
- `foundation.csv`：整合后的季度基础数据表。

## 版本管理与溯源
- Git 主分支：`main`，远程仓库：`origin`  
  `https://github.com/pjhappy-1999/analyse.pjhaapy.git`
- 提交规范：
  ```bash
  git add .
  git commit -m "feat: 新增波动率计算与滞后性分析模块，优化可视化交互"
  git push
  ```

## 路线图
- [x] 分作物计算季度波动率（基于WFP数据）
- [x] 实现波动率与GDP的滞后相关性分析（Lag 0-8）
- [x] 前端增加交互式球体选择器与可视化优化
- [ ] 引入更加系统的分布式滞后回归（DL/ARDL）对比
- [ ] 增加更多宏观经济指标作为控制变量
