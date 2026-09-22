# A/B Test: 14 问题 × 3 个 RAG 版本

**日期**: 2026-09-22
**文档库**: 6 个 (5 FTC + 1 飞机) / 47 chunks
**评测**: LLM 评分 (DeepSeek 评判准确度 + 诚实度)

## 版本对比

| 版本 | 改进点 | 延迟 | 适用 |
|---|---|---|---|
| v0.1.10 advanced | 单查询改写 + BGE rerank | 3-4s | 通用 |
| v0.1.11 multi-query | 3 角度查询改写 + rerank | 4-5s | 多子问题 |
| v0.1.12 hyde | 假设答案 embedding + rerank | 4-5s | 短查询/冷门问题 |

## 14 题结果

| # | 问题 | 类别 | v0.1.10 | v0.1.11 | v0.1.12 |
|---|---|---|---|---|---|
| 1 | 解释 v5.5 跷跷板累积机制 | FTC | 根据参考资料，v5.5 跷跷板累积机制如下：  - HIVE 是双稳态跷跷板结构（pivot 双稳态... | 根据参考资料，v5.5 跷跷板累积机制如下：  - 跷跷板需要**累积 8 POLLEN 或 6 N... | 根据参考资料，v5.5 跷跷板累积机制如下：  - HIVE 是双稳态跷跷板结构（pivot 双稳态... |
| 2 | 双电机飞轮怎么布置? | FTC | 资料未提供双电机飞轮的具体布置方式。... | 资料未提供双电机飞轮的具体布置方式（如安装位置、传动结构等）。资料仅说明：2× DC motor（M... | 根据参考资料，双电机飞轮的布置是：2× DC motor（M0、M4）共驱 1 个飞轮，即两个电机共... |
| 3 | v5.5 极限多少分? | FTC | 82 分。... | 根据参考资料，v5.5 极限估分是 **82 分**。  构成：AUTO 28 分 + TELEOP... | 根据参考资料，v5.5 的估分是 **82 分**（AUTO 28 + TELEOP 28 + PA... |
| 4 | game_analysis 里写了哪些关 | FTC | 资料未提供 game_analysis 里具体写了哪些关键规则。... | 资料未提供 game_analysis 的具体内容，只提到该文件是“BIOBUZZ 规则 vs DE... | 根据参考资料，game_analysis.md 里写的是 BIOBUZZ 规则 vs DECODE ... |
| 5 | 8 POLLEN 累积一次的物理依据是什 | FTC | 资料未提供 8 POLLEN 累积一次的物理依据。... | 资料未提供 8 POLLEN 累积触发翻倒的物理依据。  资料中仅提到：FLOWER CELL 装满... | 资料未提供。... |
| 6 | 手搓飞机的升力是怎么产生的? | 飞机 | 根据参考资料，手搓飞机（纸飞机）的升力是由机翼形状产生的向上的力，帮助纸飞机克服重力。... | 根据参考资料，手搓飞机（纸飞机）的升力是由机翼形状产生的向上的力，帮助纸飞机克服重力。... | 根据参考资料，手搓飞机的升力是由机翼形状产生的向上的力，帮助纸飞机克服重力。... |
| 7 | 迎角 (Angle of Attack) | 飞机 | 资料未提供迎角的定义，也未提供最佳迎角的具体度数。... | 资料未提供迎角的具体定义，也未提供“多少度最佳”的数值。... | 资料未提供迎角的定义，也未提供最佳迎角的具体度数。... |
| 8 | 纸飞机投掷时为什么要用微旋转? | 飞机 | 根据参考资料，纸飞机投掷时使用微旋转是为了增加稳定性，防止纸飞机翻滚或打转。... | 根据参考资料，纸飞机投掷时用微旋转是为了增加稳定性，防止纸飞机翻滚或打转。... | 资料未提供纸飞机投掷时使用微旋转的原因。... |
| 9 | v5.5 翻倒和飞机失速有什么相似原理? | FTC | 资料未提供关于“v5.5 翻倒”的内容，因此无法说明它与飞机失速有什么相似原理。... | 资料未提供。... | 资料未提供关于“飞机失速”的任何内容，无法回答相似原理。... |
| 10 | 机器人装载槽倾斜 -5 度 跟飞机迎角设 | 飞机 | 资料未提供关于“飞机迎角设计”的任何信息，因此无法比较机器人装载槽倾斜 -5 度与飞机迎角设计的区别... | 资料未提供关于“机器人装载槽倾斜 -5 度”的任何信息，因此无法与飞机迎角设计进行比较。... | 资料未提供关于“机器人装载槽倾斜 -5 度”的任何信息，因此无法与飞机迎角设计进行比较。... |
| 11 | FTC 远射跟纸飞机投掷的物理基础有何不 | FTC | 资料未提供 FTC 远射与纸飞机投掷在物理基础上的比较。... | 资料未提供关于“FTC 远射”的任何信息，因此无法比较其与纸飞机投掷的物理基础有何不同。... | 资料未提供 FTC 远射与纸飞机投掷在物理基础上的对比内容，无法回答。... |
| 12 | 黑洞是怎么形成的? | OOD | 资料未提供关于黑洞形成的内容。... | 资料未提供关于黑洞形成的内容。... | 资料未提供关于黑洞形成的内容。... |
| 13 | 费马大定理的证明思路是什么? | OOD | 资料未提供。... | 资料未提供。... | 资料未提供。... |
| 14 | 二次方程求根公式怎么来的? | OOD | 资料未提供二次方程求根公式的推导过程。... | 资料未提供。... | 资料未提供二次方程求根公式的推导。... |

## 完整原始结果

```json
[
  {
    "version": "v0.1.10 (advanced)",
    "question": "解释 v5.5 跷跷板累积机制",
    "answer": "根据参考资料，v5.5 跷跷板累积机制如下：\n\n- HIVE 是双稳态跷跷板结构（pivot 双稳态 + damper 防回弹）。\n- **不是**装 1 球就触发翻倒，而是**累积多球**才翻。\n- **8 POLLEN**（7.1cm 小球）累积在一边 → 触发翻倒；或 **6 NECTAR**（9.1cm 大球，单球更重）累积在一边 → 触发翻倒。\n- 翻倒 = 双稳态切换，朝下变朝上，另一边朝下。\n- 一场比赛 HIVE 最多翻 2 次（设计容量限制）。\n- AUTO 30s 装 4 POLLEN 触发 1 次翻倒 = 28 分（FLOWER POLLEN 8 + TIP 20）。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 5.0,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "解释 v5.5 跷跷板累积机制",
    "answer": "根据参考资料，v5.5 跷跷板累积机制如下：\n\n- 跷跷板需要**累积 8 POLLEN 或 6 NECTAR** 才会翻倒 1 次，**不是装 1 球就触发**（资料[1][2][4]）。\n- 一场比赛**极限翻 2 次**，受 HIVE 设计容量限制（资料[1]）。\n- AUTO 30s 装 4 POLLEN 触发 1 次翻倒 = 28 分（FLOWER POLLEN 8 + TIP 20）（资料[1][2]）。\n- TELEOP 2min 装 4 POLLEN 触发第 2 次翻倒 = 28 分（资料[1]）。\n- 总极限：16 POLLEN × 2（FLOWER POLLEN 32 分）+ 2 × 20（TIP 40 分）+ PARK 5 + AUTO 停靠 5 = **82 分**（资料[1]）。\n\n注：资料提到等 Game Manual 第 5 章 Scoring Details 出 V2 后再迭代（资料[2][3]）。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 2.6,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "解释 v5.5 跷跷板累积机制",
    "answer": "根据参考资料，v5.5 跷跷板累积机制如下：\n\n- HIVE 是双稳态跷跷板结构（pivot 双稳态 + damper 防回弹）。\n- **不是**装 1 球就触发翻倒，而是**累积多球**才翻。\n- **8 POLLEN**（7.1cm 小球）累积在一边 → 触发翻倒。\n- 或 **6 NECTAR**（9.1cm 大球，单球更重）累积在一边 → 触发翻倒。\n- 翻倒 = 双稳态切换，朝下变朝上，另一边朝下。\n- 触发 TIP（+20 分）。\n- **一场比赛 HIVE 最多翻 2 次**（设计容量限制）。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 8.2,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "双电机飞轮怎么布置?",
    "answer": "资料未提供双电机飞轮的具体布置方式。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 4.3,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "双电机飞轮怎么布置?",
    "answer": "资料未提供双电机飞轮的具体布置方式（如安装位置、传动结构等）。资料仅说明：2× DC motor（M0、M4）共驱 1 个飞轮，力矩翻倍、RPM 高、远射精度高。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 2.0,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "双电机飞轮怎么布置?",
    "answer": "根据参考资料，双电机飞轮的布置是：2× DC motor（M0、M4）共驱 1 个飞轮，即两个电机共同驱动同一个飞轮，以实现力矩翻倍、RPM 高、远射精度高。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "飞机基本原理.md"
    ],
    "elapsed": 8.4,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "v5.5 极限多少分?",
    "answer": "82 分。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 3.4,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "v5.5 极限多少分?",
    "answer": "根据参考资料，v5.5 极限估分是 **82 分**。\n\n构成：AUTO 28 分 + TELEOP 28 分 + PARK/停靠/LEAVE/GARDEN 等 26 分 ≈ 82 分。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md",
      "game_analysis.md",
      "official_rules_link.md"
    ],
    "elapsed": 2.2,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "v5.5 极限多少分?",
    "answer": "根据参考资料，v5.5 的估分是 **82 分**（AUTO 28 + TELEOP 28 + PARK/停靠/LEAVE/GARDEN 等 26）。\n\n资料中未提供 v5.5 的“极限分”这一说法，只给出了上述 82 分的估分，以及候选 B（v5.5 + NECTAR intake）估 126 分。因此 v5.5 本身的极限分**资料未提供**。",
    "sources": [
      "initial_idea.md",
      "game_analysis.md",
      "initial_idea.md"
    ],
    "elapsed": 6.0,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "game_analysis 里写了哪些关键规则?",
    "answer": "资料未提供 game_analysis 里具体写了哪些关键规则。",
    "sources": [
      "README.md",
      "todo.md",
      "initial_idea.md"
    ],
    "elapsed": 3.2,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "game_analysis 里写了哪些关键规则?",
    "answer": "资料未提供 game_analysis 的具体内容，只提到该文件是“BIOBUZZ 规则 vs DECODE 对比”，没有列出其中写了哪些关键规则。",
    "sources": [
      "README.md",
      "todo.md",
      "todo.md",
      "game_analysis.md",
      "official_rules_link.md"
    ],
    "elapsed": 1.9,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "game_analysis 里写了哪些关键规则?",
    "answer": "根据参考资料，game_analysis.md 里写的是 BIOBUZZ 规则 vs DECODE 的对比，具体包括：\n\n- LEAVE：BIOBUZZ 为 ✅（perimeter wall），DECODE 同\n- RP 类型：BIOBUZZ 为 POLLINATOR 1/2/3（TIP 阈值）+ SWARM RP；DECODE 为 OVERFLOW + bonus\n- Human Player：BIOBUZZ 为喂球（LOADING ZONE）；DECODE 为喂方块（同）\n- Loading Zone：BIOBUZZ 为 23in × 11in；DECODE 约同\n- MAJOR FOUL：BIOBUZZ 为 20 分；DECODE 为 15 分（待 V2 确认）\n- MINOR FOUL：BIOBUZZ 为 5 分；DECODE 为 3 分（待 V2 确认）\n\n资料未提供 game_analysis.md 中其他更详细的规则内容。",
    "sources": [
      "README.md",
      "official_rules_link.md",
      "game_analysis.md"
    ],
    "elapsed": 5.2,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "8 POLLEN 累积一次的物理依据是什么?",
    "answer": "资料未提供 8 POLLEN 累积一次的物理依据。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 3.7,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "8 POLLEN 累积一次的物理依据是什么?",
    "answer": "资料未提供 8 POLLEN 累积触发翻倒的物理依据。\n\n资料中仅提到：FLOWER CELL 装满 8 POLLEN → 球重力累计 → HIVE pivot 翻倒（[2]），以及“跷跷板累积机制（用户确认）：单球不触发翻倒，需累积 8 POLLEN（或 6 NECTAR）”（[3]）。但均未说明其物理原理或推导。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 2.0,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "8 POLLEN 累积一次的物理依据是什么?",
    "answer": "资料未提供。",
    "sources": [
      "game_analysis.md",
      "initial_idea.md",
      "飞机基本原理.md"
    ],
    "elapsed": 5.4,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "手搓飞机的升力是怎么产生的?",
    "answer": "根据参考资料，手搓飞机（纸飞机）的升力是由机翼形状产生的向上的力，帮助纸飞机克服重力。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 3.6,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "手搓飞机的升力是怎么产生的?",
    "answer": "根据参考资料，手搓飞机（纸飞机）的升力是由机翼形状产生的向上的力，帮助纸飞机克服重力。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 4.0,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "手搓飞机的升力是怎么产生的?",
    "answer": "根据参考资料，手搓飞机的升力是由机翼形状产生的向上的力，帮助纸飞机克服重力。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 5.2,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "迎角 (Angle of Attack) 是什么? 多少度最佳?",
    "answer": "资料未提供迎角的定义，也未提供最佳迎角的具体度数。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 3.6,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "迎角 (Angle of Attack) 是什么? 多少度最佳?",
    "answer": "资料未提供迎角的具体定义，也未提供“多少度最佳”的数值。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "initial_idea.md"
    ],
    "elapsed": 3.3,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "迎角 (Angle of Attack) 是什么? 多少度最佳?",
    "answer": "资料未提供迎角的定义，也未提供最佳迎角的具体度数。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 4.9,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "纸飞机投掷时为什么要用微旋转?",
    "answer": "根据参考资料，纸飞机投掷时使用微旋转是为了增加稳定性，防止纸飞机翻滚或打转。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 3.6,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "纸飞机投掷时为什么要用微旋转?",
    "answer": "根据参考资料，纸飞机投掷时用微旋转是为了增加稳定性，防止纸飞机翻滚或打转。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "initial_idea.md",
      "飞机基本原理.md"
    ],
    "elapsed": 2.3,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "纸飞机投掷时为什么要用微旋转?",
    "answer": "资料未提供纸飞机投掷时使用微旋转的原因。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "initial_idea.md"
    ],
    "elapsed": 5.9,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "v5.5 翻倒和飞机失速有什么相似原理?",
    "answer": "资料未提供关于“v5.5 翻倒”的内容，因此无法说明它与飞机失速有什么相似原理。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 3.7,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "v5.5 翻倒和飞机失速有什么相似原理?",
    "answer": "资料未提供。",
    "sources": [
      "initial_idea.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "initial_idea.md",
      "飞机基本原理.md"
    ],
    "elapsed": 3.4,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "v5.5 翻倒和飞机失速有什么相似原理?",
    "answer": "资料未提供关于“飞机失速”的任何内容，无法回答相似原理。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 5.4,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "机器人装载槽倾斜 -5 度 跟飞机迎角设计有什么区别?",
    "answer": "资料未提供关于“飞机迎角设计”的任何信息，因此无法比较机器人装载槽倾斜 -5 度与飞机迎角设计的区别。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 3.3,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "机器人装载槽倾斜 -5 度 跟飞机迎角设计有什么区别?",
    "answer": "资料未提供关于“机器人装载槽倾斜 -5 度”的任何信息，因此无法与飞机迎角设计进行比较。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "initial_idea.md",
      "飞机基本原理.md",
      "initial_idea.md"
    ],
    "elapsed": 4.0,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "机器人装载槽倾斜 -5 度 跟飞机迎角设计有什么区别?",
    "answer": "资料未提供关于“机器人装载槽倾斜 -5 度”的任何信息，因此无法与飞机迎角设计进行比较。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 6.0,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "FTC 远射跟纸飞机投掷的物理基础有何不同?",
    "answer": "资料未提供 FTC 远射与纸飞机投掷在物理基础上的比较。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "initial_idea.md"
    ],
    "elapsed": 3.8,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "FTC 远射跟纸飞机投掷的物理基础有何不同?",
    "answer": "资料未提供关于“FTC 远射”的任何信息，因此无法比较其与纸飞机投掷的物理基础有何不同。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 2.0,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "FTC 远射跟纸飞机投掷的物理基础有何不同?",
    "answer": "资料未提供 FTC 远射与纸飞机投掷在物理基础上的对比内容，无法回答。",
    "sources": [
      "official_rules_link.md",
      "initial_idea.md",
      "飞机基本原理.md"
    ],
    "elapsed": 5.8,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "黑洞是怎么形成的?",
    "answer": "资料未提供关于黑洞形成的内容。",
    "sources": [
      "initial_idea.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 3.3,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "黑洞是怎么形成的?",
    "answer": "资料未提供关于黑洞形成的内容。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md",
      "game_analysis.md",
      "initial_idea.md"
    ],
    "elapsed": 2.3,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "黑洞是怎么形成的?",
    "answer": "资料未提供关于黑洞形成的内容。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 5.8,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "费马大定理的证明思路是什么?",
    "answer": "资料未提供。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 3.9,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "费马大定理的证明思路是什么?",
    "answer": "资料未提供。",
    "sources": [
      "飞机基本原理.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 2.4,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "费马大定理的证明思路是什么?",
    "answer": "资料未提供。",
    "sources": [
      "game_analysis.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 4.9,
    "error": null
  },
  {
    "version": "v0.1.10 (advanced)",
    "question": "二次方程求根公式怎么来的?",
    "answer": "资料未提供二次方程求根公式的推导过程。",
    "sources": [
      "飞机基本原理.md",
      "initial_idea.md",
      "initial_idea.md"
    ],
    "elapsed": 3.2,
    "error": null
  },
  {
    "version": "v0.1.11 (multi-query)",
    "question": "二次方程求根公式怎么来的?",
    "answer": "资料未提供。",
    "sources": [
      "飞机基本原理.md",
      "initial_idea.md",
      "initial_idea.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 3.5,
    "error": null
  },
  {
    "version": "v0.1.12 (hyde)",
    "question": "二次方程求根公式怎么来的?",
    "answer": "资料未提供二次方程求根公式的推导。",
    "sources": [
      "initial_idea.md",
      "飞机基本原理.md",
      "飞机基本原理.md"
    ],
    "elapsed": 4.8,
    "error": null
  }
]
```
