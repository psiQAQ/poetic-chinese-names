# 中文起名方案说明

## 背景

这个项目最初目标很直接：

1. 从两个现有开源起名仓库 [`get_chinese_name`](https://github.com/wrk226/get_chinese_name) 与 [`gushi_namer`](https://github.com/holynova/gushi_namer) 里拿到可追溯、可复现的候选名字；
2. 保留尽量完整的出处信息（命中句子、原文、作者、篇名、书名、朝代）；
3. 用 [`ChineseNames`](https://github.com/psychbruce/ChineseNames) 数据库补充统计评估，让筛选不只靠主观感觉；
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

当前默认使用一个主脚本完成整条流水线：

1. **候选生成**（按参数从一个或多个数据库抽样）
2. **统计评估**（默认自动调用 ChineseNames 评估）
3. **中文化与排序裁剪**（默认按名字独特性排序并保留前 `top-n`）

对应主脚本：`scripts/generate_names.py`。
高级模式下，仍可单独使用：

- `scripts/enrich_generated_names_with_chinesenames.py`
- `scripts/rank_and_localize_names.py`

流程图（逻辑）：

`按需选择数据库 -> 生成候选 -> 合并为单一JSON -> ChineseNames评估 -> 全中文键 -> 按最大名字独特性排序 -> 保留前 top-n`

仓库依赖通过 Git Submodule 管理，位于 `submodules/`：

- `submodules/get_chinese_name`
- `submodules/gushi_namer`
- `submodules/ChineseNames`

---

## 使用的库与作用

### 1) [get_chinese_name](https://github.com/wrk226/get_chinese_name)

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

### 2) [gushi_namer](https://github.com/holynova/gushi_namer)

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

### 3) [ChineseNames](https://github.com/psychbruce/ChineseNames)

- 作用：提供姓名统计数据库（1930-2008）与姓名字符指标。
- 在本方案中的贡献：
  - 姓氏独特性、名字独特性、性别倾向、积极度等量化指标；
  - 支持按统计特征做可解释筛选。

---

## 输出 JSON 结构与字段说明

当前输出 JSON 的顶层结构如下：

- `设置参数`：本次运行使用的全部关键参数
- `候选姓名`：姓名记录数组

`候选姓名` 内每条记录（排序后）主要字段如下：

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

## 脚本使用方法

以下命令默认在项目根目录执行，推荐使用 `uv` 管理环境。

### 0) 环境配置（首次）

1) 递归克隆仓库（包含子模块）

```bash
git clone --recursive https://github.com/psiQAQ/poetic-chinese-names
cd poetic-chinese-names
```

2) 如果你之前已经 clone 过，先同步子模块

```bash
git submodule update --init --recursive
```

3) 使用 `uv` 初始化并安装依赖

```bash
# 仅当仓库没有 pyproject.toml 时需要
uv init

# 根据 pyproject.toml + uv.lock 创建/同步 .venv
uv sync
```

4) 后续运行脚本统一使用

```bash
uv run python <script.py> [args]
```

### 1) 生成结果 JSON

基础命令：

```bash
uv run python scripts/generate_names.py --count 1000 --databases all
```

参数说明（`scripts/generate_names.py`）：

| 参数名 | 说明 | 默认值 |
|---|---|---|
| `--base-dir` | 项目根目录 | `.` |
| `--surname` | 姓氏 | `王` |
| `--gender` | 性别过滤，可选 `男/女/双/不限` | `男` |
| `--given-length` | 名字字数，可选 `1/2` | `2` |
| `--count` | 总生成数量（随机从指定或默认全部数据库合并后抽样） | `50` |
| `--seed` | 随机种子（整数；同参数下可复现同一批结果） | `20260226` |
| `--databases` | 数据库选择（支持空格/逗号、多值） | `all` |
| `--excluded-file` | 禁用字文件路径（默认只看这个文件） | `configs/excluded_chars.txt` |
| `--excluded` | 额外禁用字符（仅在传入时追加） | 空字符串 |
| `--enable-chinesenames-eval` | 是否在生成后直接做 ChineseNames 评估（可用 `--disable-chinesenames-eval` 关闭） | 开启 |
| `--enable-rank` | 是否在评估后按“名字独特性”排序并中文键名化（可用 `--disable-rank` 关闭） | 开启 |
| `--top-n` | 启用排序时保留前 N 个 | `100` |
| `--output-dir` | 输出目录 | `outputs` |
| `--output-file` | 输出文件名（留空则按时间命名） | 空字符串 |
| `--list-databases` | 列出可用数据库并退出 | 关闭 |

输出说明（紧跟参数）：

- 输出目录：`outputs/`
- 默认文件名：`YYYY-MM-DD-HH-MM-SS.json`
- 若传 `--output-file`，按你指定文件名写入

数据库选择规则：

- `all`：调用全部数据库
- `get_chinese_name`：调用 `get_chinese_name` 下全部数据库
- `gushi_namer`：调用 `gushi_namer` 下全部数据库
- 也可直接传缩写：如 `gcn_sj gsn_sc` 或 `gcn_sj,gsn_sc`

### 2) 不评估和排序（全部数据库输出 100 条）

```bash
uv run python scripts/generate_names.py --count 100 --databases all --disable-chinesenames-eval
```

### 3) 高级用法（可选）

- 关闭评估：`--disable-chinesenames-eval`（关闭后会自动关闭排序）
- 关闭排序：`--disable-rank`
- 调整排序保留数量：`--top-n 200`（仅在启用评估时有意义）
- 若你想拆分流水线，仍可单独调用：

```bash
uv run python scripts/enrich_generated_names_with_chinesenames.py --input-files outputs/<你的文件名>.json
uv run python scripts/rank_and_localize_names.py --files outputs/<你的文件名>_evaluated.json --top-n 100
```

### 4) 参数组合案例

案例 1（推荐）：陆姓、女生、单字名，生成 1000 条并按名字独特性排序后保留前 20 条（仓库不变：诗经两个仓库）

```bash
uv run python scripts/generate_names.py \
  --surname 陆 \
  --gender 女 \
  --given-length 1 \
  --count 1000 \
  --seed 20260301 \
  --databases gcn_sj gsn_sj \
  --excluded-file configs/excluded_chars.txt \
  --excluded 煜昊 \
  --top-n 20 \
  --output-file README_example.json
```

案例 1 输出示例（前 100 行）：

```json
{
  "设置参数": {
    "base_dir": ".",
    "surname": "陆",
    "gender": "女",
    "given_length": 1,
    "count": 1000,
    "seed": 20260301,
    "excluded": "煜昊",
    "excluded_file": "configs/excluded_chars.txt",
    "output_dir": "outputs",
    "output_file": "README_example.json",
    "selected_databases": [
      "gcn_sj",
      "gsn_sj"
    ],
    "enable_chinesenames_eval": true,
    "enable_rank": true,
    "top_n": 20
  },
  "候选姓名": [
    {
      "姓名": "陆畲",
      "名字": "畲",
      "性别": "女",
      "名字笔画总数": 12,
      "来源仓库": "gushi_namer",
      "使用库名称": "诗经",
      "来源数据库缩写": "gsn_sj",
      "命中句子": "如何新畲",
      "原文": "嗟嗟臣工，敬尔在公。王厘尔成，来咨来茹。嗟嗟保介，维莫之春，亦又何求？如何新畲？于皇来牟，将受厥明。明昭上帝，迄用康年。命我众人：庤乃钱镈，奄观铚艾。",
      "作者": "佚名",
      "篇名": "臣工",
      "书名": "诗经",
      "朝代": "春秋",
      "评估": {
        "可用": false,
        "覆盖字数": 1,
        "姓氏信息": {
          "姓氏": "陆",
          "姓氏独特性": 2.43,
          "姓氏首字母序位": 12.0
        },
        "指标": {
          "姓名长度": 2,
          "姓氏独特性": 2.43,
          "姓氏首字母序位": 12.0,
          "名字用字独特性": 6.0,
          "语料字独特性": 4.997,
          "名字性别倾向": 1.0,
          "名字积极度": 2.5,
          "名字温暖度": 2.6,
          "名字能力感": 2.3
        },
        "逐字指标": [
          {
            "字符": "畲",
            "名字独特性": 6.0,
            "语料独特性": 4.997,
            "性别倾向": 1.0,
            "积极度": 2.5,
            "温暖度": 2.6,
            "能力感": 2.3
          }
        ],
        "提示": [
          "积极度偏低"
        ],
        "数据来源": "ChineseNames（1930-2008）"
      },
      "排序依据_最大名字独特性": 6.0
    },
    {
      "姓名": "陆屠",
      "名字": "屠",
      "性别": "女",
      "名字笔画总数": 11,
      "来源仓库": "get_chinese_name",
      "使用库名称": "诗经/大雅/荡之什",
      "来源数据库缩写": "gcn_sj",
      "命中句子": "韩侯出祖，出宿于屠。显父饯之，清酒百壶。其殽维何？炰鳖鲜鱼。其蔌维何？",
      "原文": "韩侯出祖，出宿于屠。显父饯之，清酒百壶。其殽维何？炰鳖鲜鱼。其蔌维何？",
      "作者": "",
      "篇名": "韩奕",
      "书名": "诗经",
      "朝代": "",
      "评估": {
        "可用": false,
        "覆盖字数": 1,
        "姓氏信息": {
          "姓氏": "陆",
          "姓氏独特性": 2.43,
          "姓氏首字母序位": 12.0
        },
        "指标": {
          "姓名长度": 2,
          "姓氏独特性": 2.43,
          "姓氏首字母序位": 12.0,
          "名字用字独特性": 6.0,
          "语料字独特性": 4.67,
```

（后续省略）

---

## 使用注意

- `评估.可用` 是规则判断结果，不等同于“名字一定好”；当前主要基于覆盖字数、性别倾向与积极度阈值。
- ChineseNames 数据覆盖到 2008 年，现代新字/异体字/冷僻字可能命中率偏低。
- 当前排序依据是“名字各字中的最大名字独特性”，更靠前不代表更适合日常使用。
- `名字笔画总数` 使用 `get_chinese_name` 的笔画表，和部分其他口径（如康熙体系）可能不同。
- 两个来源仓库原始结构不同，`作者/朝代/篇名` 等字段偶尔为空属于源数据差异。

---

## 致谢

感谢以下开源项目提供数据与能力支持：

- [get_chinese_name](https://github.com/wrk226/get_chinese_name)
- [gushi_namer](https://github.com/holynova/gushi_namer)
- [ChineseNames](https://github.com/psychbruce/ChineseNames)
