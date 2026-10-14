---
title: '人类投胎模拟器 — 用真实人口数据算一次出生概率'
description: '如果重新出生一次，你会落在哪里？237 个国家/地区、2023 年 1.32 亿例活产、独立概率引擎与蒙特卡洛模拟，以及这个项目最特别的一点：它把「自己不知道什么」也一起画了出来。'
pubDate: '2026-10-14'
---

<img src="/images/bl-hero.png" alt="人类投胎模拟器首屏" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 1｜默认场景：中国 · 城市 · 家庭收入 Top 10% · 父母本科及以上*

> 一个可以自己动手按的小实验：**如果重新出生一次，你会落在哪里？** 下面把它的玩法、概率模型、数据来源和工程实现完整写一遍。

## 一句话介绍

「人类投胎模拟器」（Human Birth Lottery）是一个**纯静态**的 Web 应用：左边叠条件，右边实时算出「地球上随机投一次胎、恰好满足这些条件」的联合概率，然后告诉你这有多稀有、模型有多不确定、物质机会大概落在什么位置。

没有后端、没有数据库、没有 API Key，整站导出成静态文件，打开就能算。

## 一次完整的投胎长什么样

条件面板分「简洁 / 高级」两档：

- **出生国家 / 地区**：237 个可搜索，也可以直接选「全球随机」或按收入组 / 地区聚合
- **居住地**：城市 / 农村
- **家庭收入**：本国百分位，滑块精确到 Top X%（模型里切成 100 个互斥收入单元）
- **父母最高学历**：7 档
- **出生健康**：三种口径 —— 非早产非低体重 / 再加上产科医疗与 28 天存活 / 早产或低体重
- **家庭结构、教育机会**：双亲 / 单亲 / 其他；基础 / 良好 / 丰富
- **基础设施**：稳定住房、专业产科医疗、互联网、饮用水、卫生设施、电力、完成初中（作为机会代理）

图 1 这套默认条件（中国 · 城市 · 收入 Top 10% · 父母本科及以上）的结果是：

**≈ 0.26%，约 380 次出生中有 1 次。**

但它同时给了三个限定语：稀有度标签 `Rare`、敏感性范围 `0.12% — 0.59%`、模型置信度 `Low`。旁边那行小字写得很清楚：

> 稀有程度，不衡量人的价值。区间为模型敏感性范围，非统计置信区间。

## 概率是怎么算出来的

<img src="/images/bl-waterfall.png" alt="概率瀑布" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 2｜FOLLOW THE PROBABILITY：每加一个条件，概率收窄到多少*

同一套默认条件，每一刀都被摊开：

| 顺序 | 条件 | 累积概率 | 保留比例 |
|---|---|---|---|
| 起点 | 全球随机出生 | 100% | — |
| 01 | 出生国家 / 地区（中国） | 6.7% | ×0.067 |
| 02 | 城市居住 | 4.4% | ×0.66 |
| 03 | 本国收入 P90–P100 | 0.44% | ×0.10 |
| 04 | 本科及以上父母 | 0.31% | ×0.70 |
| 05 | 出生健康（联合条件） | 0.26% | ×0.86 |

<img src="/images/bl-contributors.png" alt="稀有度来源" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 3｜WHAT MAKES THIS RARE?：国家 ×0.067 切得最狠，收入 ×0.103 次之，城乡 ×0.66*

底层是一条带条件的生成链：

```
Country ~ 年度出生人数
  └ Residence | Country
     └ Income | Country, Residence
        └ ParentEducation | Country, Residence, Income
           ├ Healthcare | Country, Residence, Income, ParentEducation
           │   └ Preterm → LowWeight → NeonatalSurvival
           ├ EducationOpportunity
           ├ Infrastructure / Completion
           └ MaternalAge
```

实现上有个关键选择：**枚举，而不是把几个百分比乘一乘**。在固定离散网格上枚举国家 × 城乡 × 100 个互斥收入单元 × 7 档学历 × 2 种医疗状态，没选的变量做边际化，其余叶节点解析消元。好处很实在：

- 收入区间正确嵌套（Top 1% 是 Top 10% 的子集）
- 多一个限制条件，概率不会变大
- 早产 / 低体重 / 存活三项联合枚举，同一份健康证据不会被重复折损
- 互相矛盾的条件（比如配出不可能的早产 + 低体重组合）直接判 0 并给出提示

对外暴露 5 个接口：`calculateProbability()`、`calculateConditionalProbability()`（取证据交集）、`generateRandomBirth()`、`simulateBirths(n)`（上限 5 万）、`compareConfigurations(a,b)`（替换参数）。整个引擎跑在 **Web Worker** 里，不卡界面。

## 数据从哪来

`data/countries.json` 是**构建期的离线快照**，不是实时抓取：

- 出生权重来自 UN World Population Prospects 2024（经 OWID 传输）：2023 年覆盖 237 个国家/地区共 **132,088,956** 例活产，WPP 世界总量 132,110,264 —— 覆盖率 **99.9839%**，剩下的差额如实标注，**不摊派给任何国家**
- 9 个国别指标来自 World Bank 与 WHO：城市化、互联网使用人口、基本卫生设施、基本饮用水、电力覆盖、专业人员接生比例、新生儿死亡率、高等教育毛入学率、初中完成率
- 每条指标都带来源 URL、指标代码、年份、数值和类型；缺失值按同地区出生加权均值回退，地区也缺再用全球回退

用**当年活产人数**加权而不是人口比例，这一点很关键 —— 否则出生大国会被系统性低估。

## 我觉得最难得的地方：它把「不知道」也一起画了出来

<img src="/images/bl-tooltip.png" alt="条件说明浮层" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 4｜每个条件都写明它是什么、以及它不是什么*

随便点开几个条件的说明：

- 收入：100 个互斥收入单元，条件于城乡并做生育率倾斜，**不是全球收入排名**
- 学历：国家高等教育毛入学率**只是背景代理，不等于父母学历比例**
- 互联网：个体使用率转成的**家庭可及性代理，不是家庭接入实测**
- 饮用水：World Bank / WHO–UNICEF JMP 的基本饮用水服务，**不等同于更严格的「安全管理饮用水」指标**
- 初中完成率：转成「未来完成机会」的模型代理，**不是高中完成率**
- 中国单独说明：户籍与实际居住地不同，第一版未建模户籍 —— 所以它没有拿城市化率冒充户籍口径
- **冲突地区暴露直接禁用**：理由是「国家是否列入脆弱国家名单 ≠ 新生儿是否位于冲突地区」，没有可靠的次国家交叉数据就不做，宁可空着

数据被分成三类标注：`national-statistic`（实测）/ `proxy`（代理）/ `model-derived`（模型推），置信度按这三类分别计分。所以默认那套条件的置信度是 `Low` —— 因为收入和学历都是模型推出来的，不是观测到的。

<img src="/images/bl-methodology.png" alt="方法页" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 5｜独立的 DATA & METHODOLOGY 页：第一句就是「理解数字，也理解它的边界」*

方法页里直接把不确定性公式也公开了：

```
f = min(8, 1.35 + 0.22 × 代理条件数 + 0.25 × 回退指标类数)
显示区间 = [p/f, min(1, p×f)]
```

并明确写了：**这不是置信区间，也不代表出生估计没有误差**。

## 四个可以自己动手的实验

**① 抽一次投胎** —— 按同一套条件图采样，给你一张具体的「人生卡」：国旗、城乡、收入区间、父母年龄、有没有宽带、28 天结局。

<img src="/images/bl-birthcard.png" alt="随机投胎卡" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 6｜ONE BIRTH, ONE POSSIBLE START*

**② What-if：只改一个条件** —— 复制当前配置成 A，只改国家 / 城乡 / 收入，看概率倍数。把 B 改成美国之后，比例是 **0.49×**。

<img src="/images/bl-whatif.png" alt="配置对比" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 7｜SAME WORLD, A DIFFERENT START*

<img src="/images/bl-opportunity.png" alt="物质机会指数" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 8｜物质机会指数：由收入 30% / 医疗 20% / 教育 20% / 住房 10% / 基础设施 20% 构成的模型指标*

**③ 一万次出生** —— 蒙特卡洛把世界切开（图 9）：

<img src="/images/bl-simulation.png" alt="一万次模拟分布" style="border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">

*图 9｜10,000 次出生的切片：印度 17%、中国 7.1%、尼日利亚 5.5%、巴基斯坦 4.9%…*

同一轮模拟还给出：城市出生 **51%**、早产 **10%**、低出生体重 **15%**、28 天存活 **98%**；父母最高学历分布里，**博士占 1.1%**、小学及以下占 27%。柱状是本轮样本频率，虚线是 UN WPP 的理论份额 —— 两者对得上，说明采样确实按出生人数加权，而不是每个国家等概率。

**④ 深色模式 + 移动端** —— 响应式是认真做过的，390px 无横向溢出。

<div style="display:flex; gap:14px; align-items:flex-start;">
<img src="/images/bl-dark.png" alt="深色模式" style="width:62%; border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">
<img src="/images/bl-mobile.png" alt="移动端" style="width:34%; border-radius: 12px; border: 2px solid #000; box-shadow: 5px 5px 0 #A8D5E2;">
</div>

*图 10｜深色模式与 390px 移动端布局*

## 工程实现

| 项 | 情况 |
|---|---|
| 技术栈 | Next.js 16 + React 19 + TypeScript，`output: 'export'` 纯静态导出 |
| 代码分工 | `probabilityEngine.ts` 确定性联合概率 / `model.ts` 条件分布与代理回退 / `random.ts` 拓扑采样 / `engine.worker.ts` 独立线程 / `state.ts` URL 校验与序列化 |
| 可分享 | 全部主配置编码进 URL，刷新自动恢复；剪贴板不可用时给手动复制降级 |
| 测试 | 20 项核心模型测试：归一化、概率范围、嵌套 / 互斥事件、限制单调性、冗余健康证据、5 万次国家频率收敛、蒙特卡洛与精确边际一致、URL 回环、缺失数据回退 |
| 浏览器 QA | Playwright 覆盖实时计算、矛盾条件、URL 刷新恢复、随机卡、配置比较、1 万次 Worker 模拟、深色模式、390px 布局与方法页路由 |
| 其他 | ESLint / TypeScript / 生产构建全绿，npm audit 0 项已知漏洞；WebMCP 渐进增强 —— 支持的浏览器里可以通过 `generate_random_birth` 操作同一张投胎卡，不支持也不影响普通功能 |

## 它自己承认的边界

- 家庭结构、住房、母亲年龄、兄弟姐妹、收入相关系数、父母学历分布：都是**公开标注的探索性先验，不是观测数据**；系数未用 DHS / MICS 微观数据拟合
- 健康模型没有额外连入母亲年龄
- 教育机会的三档（基础 / 良好 / 丰富）不是 UNESCO 官方分类
- 只覆盖 2023 一个年份
- 户籍、父亲独立年龄 / 学历、重大先天异常、疫苗可及：未建模
- PPP 家庭收入与官方不确定性区间：未导入

## 写在最后

同类产品很容易在「这个数字到底有多可靠」这一步含糊过去，这个项目反其道而行：把模型假设、代理性质、数据缺口全部前置到界面上，让每个人都能看到哪些数字是称出来的、哪些是估出来的。

它想说的是**起点的不平等有多具体**；而它做到的是，对「自己算得有多不准」同样具体。

下一步的路线图也写在仓库里了：用 DHS / MICS 这类微观数据校准城乡、收入、父母学历的联合结构，导入次国家冲突暴露与 PPP 家庭收入，再对参数后验做抽样与样本外验证 —— 只有走到那一步，现在这套透明的敏感性提示才能升级成有统计支持的不确定性范围。
