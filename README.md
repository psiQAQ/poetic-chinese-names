# 中文起名方案说明

## 背景

这个项目最初目标很直接：

1. 从两个现有开源起名仓库里拿到可追溯、可复现的候选名字；
2. 保留尽量完整的出处信息（命中句子、原文、作者、篇名、书名、朝代）；
3. 用 `ChineseNames` 数据库补充统计评估，让筛选不只靠主观感觉；
4. 最终给出一份结构稳定、便于后续继续加工的 JSON 结果。

这套流程支持参数化：可自定义姓氏、性别与名字字数（单字/双字）。

---

## 目标

当前版本的输出目标是：

- 每个来源先生成 1000 个候选（可配置）；
- 避开指定禁用字集合；
- 支持单字名与双字名：
  - 双字名：两个来源都可直接生成；
  - 单字名：`get_chinese_name` 走连续单字抽取，`gushi_namer` 走句内随机单字抽样（属于后处理适配）；
- 计算每个名字的统计指标；
- 按排序规则保留前 100：
  - 规则：取“名字各字中的 `名字独特性` 最大值”，越大越靠前；
- 输出 JSON，字段统一中文键名。

---

## 设计架构

整体分 3 个阶段：

1. **候选生成**（脚本：`scripts/generate_names.py`）
2. **统计评估**（脚本：`scripts/enrich_generated_names_with_chinesenames.py`）
3. **中文化与排序裁剪**（脚本：`scripts/rank_and_localize_names.py`）

流程图（逻辑）：

`按需选择数据库 -> 生成候选 -> 合并为单一JSON -> ChineseNames评估 -> 全中文键 -> 按最大名字独特性排序 -> 保留前100`

仓库依赖通过 Git Submodule 管理，位于 `submodules/`：

- `submodules/get_chinese_name`
- `submodules/gushi_namer`
- `submodules/ChineseNames`

---

## 使用的库与作用

### 1) get_chinese_name

- 作用：从诗经/唐诗等语料抽取候选，做规则过滤。
- 在本方案中的贡献：
  - 提供候选名；
  - 提供部分出处上下文；
  - 提供姓名性别过滤集合与笔画字典（数据文件）。

可用数据库：

| 数据库中文名 | 调用缩写名 |
|---|---|
| 诗经 | `gcn_sj` |
| 唐诗 | `gcn_ts` |

### 2) gushi_namer

- 作用：从诗词 JSON 中随机抽样，生成带出处的名字。
- 在本方案中的贡献：
  - 候选名多样性；
  - 出处信息相对完整（句子、原文、作者、篇名、书名、朝代）。

可用数据库：

| 数据库中文名 | 调用缩写名 |
|---|---|
| 诗经 | `gsn_sj` |
| 楚辞 | `gsn_cc` |
| 唐诗 | `gsn_ts` |
| 宋词 | `gsn_sc` |
| 乐府 | `gsn_yf` |
| 古诗 | `gsn_gs` |
| 辞赋 | `gsn_cf` |

### 3) ChineseNames

- 作用：提供姓名统计数据库（1930-2008）与姓名字符指标。
- 在本方案中的贡献：
  - 姓氏独特性、名字独特性、性别倾向、积极度等量化指标；
  - 支持按统计特征做可解释筛选。

---

## 输出 JSON 字段说明

当前最终结果（排序后）主要字段如下：

- `姓名`：完整姓名（示例：王某某）
- `名字`：去掉姓后的名字（支持单字或双字）
- `性别`：按生成参数写入
- `名字笔画总数`：名字各字笔画总和
- `来源仓库`：`get_chinese_name` 或 `gushi_namer`
- `使用库名称`：语料来源（如诗经、唐诗、宋词等）
- `来源数据库缩写`：数据库调用缩写（如 `gcn_sj`、`gsn_sc`）
- `命中句子`：生成时命中的那一句
- `原文`：对应段落或全文上下文
- `作者` / `篇名` / `书名` / `朝代`：出处元信息
- `评估`：ChineseNames 的统计评估对象
- `排序依据_最大名字独特性`：本次排序使用的分值

`评估` 下的字段：

- `可用`：按当前规则给出的可用性判断
- `覆盖字数`：名字字符中，被 ChineseNames 收录并命中的字数
- `姓氏信息`：姓氏相关指标
- `指标`：姓名层面的聚合指标
- `逐字指标`：每个字的指标
- `提示`：不满足条件时的原因提示
- `数据来源`：当前写死为 ChineseNames（1930-2008）

---

## 容易引起歧义或标准不明确的点

### 1) “可用”不是绝对结论

`可用` 是规则判断，不是“名字好坏”的终局结论。当前只看：

- 名字各字都能在 ChineseNames 命中；
- `名字性别倾向` 不偏女性；
- `名字积极度` 不低于阈值（当前 2.8）。

如果你的偏好不同（更文雅、更中性、强调积极度），要改阈值。

### 2) “覆盖字数”受数据库年代影响

ChineseNames 数据覆盖到 2008 年，现代新字、异体字、冷僻字命中率会受影响。

### 3) “名字独特性”越高不等于越适合

本方案排序依据是“名字各字里更独特的那个字”。
这会把一些非常稀有字顶到前面，但可能带来：

- 生僻难写；
- 读音辨识差；
- 实际社交使用成本高。

建议后续再加一层“可读性/常用字”过滤。

### 4) 笔画口径

`名字笔画总数` 使用的是 `get_chinese_name` 数据里的笔画表，不等同于所有流派（如部分康熙字典口径）。

### 5) 出处字段完整度不完全一致

两个来源的原始数据结构不同，少数字段可能为空（例如部分作者缺失），这是源数据差异，不是脚本异常。

---

## 脚本使用方法

以下命令默认在项目根目录执行，推荐使用 `.venv` 里的 Python。

### 0) 克隆（包含子模块）

```bash
git clone --recursive <你的仓库地址>
```

如果已经 clone 过：

```bash
git submodule update --init --recursive
```

### 1) 生成候选（单个 JSON 输出）

```bash
.venv/bin/python scripts/generate_names.py --count 1000 --databases all
```

可选参数（核心）：

- `--surname`：姓氏，默认 `王`
- `--gender`：`男 | 女 | 双 | 不限`，默认 `男`
- `--given-length`：`1 | 2`，默认 `2`
- `--databases`：可选一个或多个数据库缩写（支持空格或逗号分隔）
- `--output-file`：输出 JSON 文件名，默认 `generated_names.json`
- `--list-databases`：打印可用数据库及缩写并退出

数据库选择规则：

- `all`：调用全部数据库
- `get_chinese_name`：调用 `get_chinese_name` 下全部数据库
- `gushi_namer`：调用 `gushi_namer` 下全部数据库
- 也可直接传缩写：如 `gcn_sj gsn_sc` 或 `gcn_sj,gsn_sc`

示例 1：生成“李姓、女生、单字名”，只使用诗经（两个仓库）

```bash
.venv/bin/python scripts/generate_names.py --surname 李 --gender 女 --given-length 1 --count 1000 --databases gcn_sj gsn_sj
```

示例 2：只使用 `gushi_namer` 的楚辞和宋词

```bash
.venv/bin/python scripts/generate_names.py --count 800 --databases gsn_cc,gsn_sc
```

禁用字默认读取 `configs/excluded_chars.txt`，开发者可直接增删该文件中的汉字。
也可通过参数覆盖：

```bash
.venv/bin/python scripts/generate_names.py --count 1000 --databases all --excluded-file configs/excluded_chars.txt
```

默认参数（`--surname 王 --gender 男 --given-length 2 --databases all`）时输出：

- `outputs/generated_names/generated_names.json`

### 2) 补充 ChineseNames 评估

```bash
.venv/bin/python scripts/enrich_generated_names_with_chinesenames.py
```

### 3) 中文键名化 + 排序 + 只保留前100

```bash
.venv/bin/python scripts/rank_and_localize_names.py --top-n 100
```

---

## 当前结果文件

- `outputs/generated_names/generated_names.json`

该文件已：

- 全中文键名；
- 按 `排序依据_最大名字独特性` 降序；
- 保留前 100 条。

---

## 后续建议

如果要进一步提升实用性，建议再加三层规则：

1. 常用字频过滤（减少极冷僻字）；
2. 发音可读性过滤（连读顺口、避免歧义音）；
3. 人工审阅白名单（结合家庭偏好、方言谐音、文化禁忌）。
