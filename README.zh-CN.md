# Qwen3 Embedding 推理 snap

[![qwen3-embedding](https://snapcraft.io/qwen3-embedding/badge.svg)](https://snapcraft.io/qwen3-embedding)

<!-- README-I18N:START -->

[English](./README.md) | [Português (Brasil)](./README.pt-BR.md) | **简体中文**

<!-- README-I18N:END -->

**[Qwen3-Embedding](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)** 是
[通义千问团队](https://qwen.ai)推出的文本嵌入模型系列，专为检索、语义搜索、RAG 流水线、
分类、聚类和代码搜索而设计。支持 100 多种语言（含编程语言）、32K token 输入、用户自定义
输出维度（Matryoshka）以及任务指令。8B 版本在发布时（2025 年 6 月，得分 70.58）位列
**MTEB 多语言榜单第一**。

使用本 snap 可快速安装一个优化的本地文本嵌入环境，通过 OpenAI 兼容的 `/v1/embeddings`
API 提供服务。

本 snap 包含以下针对硬件优化的推理引擎：

* cpu：针对 x64 与 ARM（armv8、armv9）CPU 优化
* nvidia-gpu：CUDA GPU 加速
* amd-gpu：AMD GPU 的 ROCm 加速

系统会根据可用硬件自动选择最合适的引擎。

#### 安装
```shell
sudo snap install qwen3-embedding
```

#### 使用
```shell
curl -s http://127.0.0.1:8362/v1/embeddings \
  -H 'Content-Type: application/json' \
  -d '{"model": "qwen3-embedding-0-6b", "input": "什么是 inference snap？"}'
```

> [!TIP]
> 部分加速器需要额外的[驱动](https://documentation.ubuntu.com/inference-snaps/how-to/setup/drivers/)才能与本 snap 配合使用。
> `amd-gpu` 引擎使用内核自带的 `amdgpu` 驱动（KFD）；ROCm 用户态库已打包在本
> snap 中，主机无需安装 ROCm。

## 模型规格

提供三种规格。默认 0.6B；使用 `sudo qwen3-embedding use-model <模型>` 切换并重启服务：

| 模型 | 权重 | 安装后磁盘 | 嵌入维度 | 说明 |
| --- | --- | --- | --- | --- |
| `qwen3-embedding-0-6b` (Q8_0) | 0.64 GB | ~1.0 GB | 1024 | 快速，适合边缘/RAG；近无损量化 |
| `qwen3-embedding-4b` (Q8_0) | 4.28 GB | ~4.7 GB | 2560 | 更高的检索质量 |
| `qwen3-embedding-8b` (Q4_K_M) | 4.68 GB | ~5.1 GB | 4096 | 最高质量（MTEB 多语言第一） |

```shell
sudo qwen3-embedding use-model qwen3-embedding-4b
sudo snap restart qwen3-embedding
```

所有权重均为通义千问团队发布的官方 GGUF
（[0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF)、
[4B](https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF)、
[8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B-GGUF)）。0.6B 与 4B 采用 Q8_0（近无损）；
8B 采用 Q4_K_M，因为官方 Q8_0 版本（8.05 GB）超出 Snap Store 单组件 5 GiB 上限，需要权重分片。

## 系统要求

在 cpu 引擎上以固定 llama.cpp 运行时实测 `llama-server` 的峰值 RSS。上下文会按可用内存
自动适配（`--fit-ctx`，下限 4096 token，上限 32K），因此 KV 缓存——以及内存占用——随空闲
内存与模型规模伸缩：

| 模型 | 权重 | KV 缓存（4096 → 32768 token） | 典型总 RSS |
| --- | --- | --- | --- |
| 0.6B | 0.64 GB | 0.45 → 3.6 GB | ~1.4 → 4.6 GB |
| 4B | 4.28 GB | 0.60 → 4.8 GB | ~5.2 → 9.4 GB |
| 8B | 4.68 GB | 0.60 → 4.8 GB | ~5.6 → 9.8 GB |

除权重外，0.6B 每 token 上下文约需 **110 KB**，4B/8B 约 **147 KB**。nvidia-gpu 引擎下
llama.cpp 会尽量把层卸载到 GPU，支持部分卸载。

安装 0.6B 后磁盘占用约 1.0 GB（snap + llama.cpp 组件 + 权重）；若选择 nvidia-gpu 引擎再
加约 1.1 GB（约 730 MB 下载）；若选择 amd-gpu 引擎，再加约 3.8 GB（约 1.1 GB 下载）。

## 使用指南

### 基础嵌入

```shell
curl -s http://127.0.0.1:8362/v1/embeddings -H 'Content-Type: application/json' -d '{
  "model": "qwen3-embedding-0-6b",
  "input": ["中国的首都是哪里？", "中国的首都是北京。"]}'
```

返回向量已做 **L2 归一化**，因此两个向量的点积即余弦相似度。响应遵循 OpenAI 嵌入格式
（`data[].embedding`、`data[].index`、`usage.prompt_tokens`）。

### 指令（检索场景推荐）

Qwen3-Embedding 支持指令：在**查询**前加上任务描述可提升检索效果约 1-5%（厂商实测；本仓库
E2E 测试在小样例上差距更大）。文档侧不加指令：

```shell
INSTRUCT="Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "
curl -s http://127.0.0.1:8362/v1/embeddings -H 'Content-Type: application/json' -d "{
  \"model\": \"qwen3-embedding-0-6b\",
  \"input\": \"${INSTRUCT}Ubuntu 的 snap 是如何工作的？\"}"
```

即使内容是非英文，指令也建议用**英文**书写：训练指令大多为英文。指令只加在查询侧——加在
文档侧会降低效果。

### 自定义维度（Matryoshka）

模型支持 Matryoshka 表示学习：截断并重新归一化后，向量的前 *N* 维仍然有效（0.6B：
32-1024，4B：至 2560，8B：至 4096）。服务端始终返回完整向量，请在客户端截断：

```python
import math
v = response["data"][0]["embedding"][:256]
v = [x / math.sqrt(sum(t*t for t in v)) for x in v]   # 截断后重新归一化
```

OpenAI 的 `dimensions` 请求参数会被内置 llama-server 接受但**忽略**（始终返回完整维度）；
请改用上述客户端截断方式。

### 长文档与批量

* 超出已适配上下文的输入会返回 HTTP 400（`exceed_context_size_error`），而不是被静默截断
  ——请对文档分块（模型的舒适区是数千 token 以内的段落）。
* 单次请求可嵌入文本列表；请保持批次的**总** token 数在上下文之内，或拆分为多次请求。

## 配置

引擎从 snap 配置读取设置：

| 配置项 | 默认值 | 用途 |
| --- | --- | --- |
| `min-context-size` | `4096` | `--fit-ctx` 下限；`--fit` 会增长上下文至模型 32K 上限 |
| `sleep-idle-seconds` | `600` | 空闲多久后 `llama-server` 卸载模型（释放内存） |
| `ubatch-size` | `512` | 提示处理的物理批次（吞吐与内存的权衡） |
| `http.port` / `http.host` | `8362` / `127.0.0.1` | OpenAI 兼容 API |
| `verbose` | `false` | 向 `llama-server` 传递 `--verbose` |

使用 `qwen3-embedding get` 查看；修改需要 root（`sudo qwen3-embedding set`），且需重启服务
生效：

```shell
qwen3-embedding get
sudo qwen3-embedding set ubatch-size=8192
sudo snap restart qwen3-embedding
```

在 CPU 上以受控负载实测（见仓库 `ai/` 文档）表明 **512**（llama.cpp 默认值）在所有文档profile上
都是最快且最省内存的选择；更大的 ubatch 会带来更大的计算缓冲（内存/显存）而在此硬件上并无收益。
在 GPU 或面向吞吐的机器上，厂商推荐的 `ubatch-size=8192` 可能更优：请先实测再更改。

## 资源

📚 **[文档](https://documentation.ubuntu.com/inference-snaps/)**，学习如何使用 inference snaps

🤗 **[模型卡](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)**，模型官方文档

📦 **[GGUF 权重](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B-GGUF)**，本 snap 内置的量化权重

🧩 **[Qwen3-Embedding 仓库](https://github.com/QwenLM/Qwen3-Embedding)**，评测代码与用法示例

📝 **[技术报告](https://arxiv.org/pdf/2506.05176)**，Qwen3 Embedding: Multilingual, Versatile, Efficient

🐛 **[Issues](https://github.com/amenezes/qwen3embedding-snap/issues)**，报告问题与需求

## 关于本 snap 的说明

* **运行时固定版本：** llama.cpp 固定为 `b10344`，与兄弟 snap（`minicpm5-2b`、`qwen3guard`）
  及 Canonical 的 `phi4`/`smollm2`/`gemma4` 相同。Qwen3 架构（含嵌入模型）支持早在 2025 年
  5 月即已进入上游，远早于该固定版本。版本升级以 Renovate PR 形式提交（不自动合并），且
  必须通过嵌入 E2E 测试（`make embed-test`）。
* **Pooling：** 引擎显式传递 `--pooling last`——Qwen3-Embedding 训练所用的末 token（EOS）
  池化。官方 GGUF 的元数据中已内置相同取值（`llama.pooling_type=LAST`）；显式传参可兼容
  丢失该元数据的再量化 GGUF。
* **无 Web UI：** 本 snap 不提供聊天界面或 webui——嵌入模型产出向量而非文本。内置
  `llama-server` 仍会对 `/v1/chat/completions` 返回无意义输出（它是基座模型）；请使用
  `/v1/embeddings`。
* **归一化：** 向量在服务端做 L2 归一化（llama.cpp `--embd-normalize` 默认值），与模型预期
  的余弦相似度用法一致。
* **模型许可证：** Apache-2.0（通义千问团队，阿里巴巴集团）。打包代码为 GPL-3.0。
* **引擎选择：** 只要 PCI 总线上存在对应厂商的 GPU，就会选择 `nvidia-gpu` 或
  `amd-gpu` 引擎，即使驱动不可用。此时后端初始化失败，llama.cpp 回退到 CPU 后端；运行
  `sudo qwen3-embedding use-engine cpu` 可切回并释放该引擎组件（NVIDIA 约 1.1 GB，
  AMD 约 3.8 GB）。AMD 引擎仅匹配内置 ROCm 构建支持的微架构
  （gfx1010–gfx1201，含 RX 9070 XT）；较旧的 AMD GPU 会选择 cpu 引擎。选择在安装时进行，
  需要 `hardware-observe` 接口；若未获自动连接，请手动连接后重新选择：
  ```shell
  sudo snap connect qwen3-embedding:hardware-observe
  sudo qwen3-embedding use-engine --auto
  ```
* **AMD 引擎需要 `process-control`：** ROCm 运行时用 `sched_setaffinity` 固定其工作线程，而 snapd
  的默认 seccomp 策略只允许 pid 0 调用该接口。缺少该插件时 HSA 无法初始化，llama.cpp 记录
  `no ROCm-capable device is detected` 并在 CPU 上运行，而引擎仍显示为 `amd-gpu`。该接口不会自动
  连接，请在安装后连接一次；发布到商店前还需申请其自动连接：
  ```shell
  sudo snap connect qwen3-embedding:process-control
  sudo snap restart qwen3-embedding.server
  ```
* **Provider：** 本 snap 导出 `inference-provider` 内容插槽，其他 snap 可直接消费该端点而
  无需自行运行模型。
* **本地 API：** 端点无鉴权并允许跨域请求。仅监听 `127.0.0.1`——请勿将 `http.host` 重绑定
  到公网接口。
* **端口：** 8362 延续 inference-snaps 家族序列（8324-8361 为 Canonical 各 snap 使用，
  8364/8365 为兄弟 snap `qwen3guard` 使用）。

## 从源码构建与安装

克隆仓库：
```shell
git clone https://github.com/amenezes/qwen3embedding-snap
```

初始化开发环境：
```shell
make init        # 默认 0.6B 权重（约 0.6 GB）+ 校验和验证
make init-all    # 全部三种规格（约 9.6 GB）
```

`snapcraft` 默认在容器内构建，因此需要先有构建 provider。使用 LXD 时初始化一次
（`--storage-backend=dir` 可避免 ZFS loop pool）：

```shell
lxd init --auto --storage-backend=dir
```

没有 provider 时，可在主机上用 `sudo snapcraft pack --destructive-mode --platform amd64`
构建。

构建并安装 snap：
```shell
make build       # 需要 init-all：三个 GGUF 将作为组件打包
make install
```

`make install` 安装 snap 和目录下所有 `.comp`，重新连接各接口，并保留已选定的引擎。若要在全新
安装中更换引擎，或在执行 `./dev/install.sh --clean`（会清除配置）之后更换，请传入 `--engine`：

```shell
./dev/install.sh --engine=amd-gpu
```

使用嵌入 E2E 测试验证运行中的服务：
```shell
make embed-test                       # 针对已安装的 snap（端口 8362）
make embed-test MODEL=qwen3-embedding-4b DIM=2560
```

如需使用本地权重副本，请放置到 `components/model-*-gguf/` 并运行 `make verify-model` /
`make verify-extra-models`；`Makefile` 中的 `GGUF_*` 变量可覆盖以指向内部镜像。

## 发布到 Snap Store

有两个商店侧申请是前置条件，且都需要时间，请尽早提交：

* **组件上传权限** —— 权重与 llama.cpp 运行时以
  [components](https://snapcraft.io/docs/explanation/how-snaps-work/snap-components/) 形式
  分发，组件上传仅限商店白名单账户。请在
  [Snapcraft 论坛](https://forum.snapcraft.io/c/store-requests/)申请。
* **`hardware-observe` 自动连接** —— 该接口默认不自动连接，商店安装时 `use-engine --auto`
  无法检测硬件，直到申请获批（参见
  [流程](https://snapcraft.io/docs/reference/administration/process-for-aliases-auto-connections-and-tracks/)）。

首次上传还需要已注册名称与真实存在的仓库：商店页面会链接 `snap/snapcraft.yaml` 中的
`website`、`source-code`、`issues` 与 `contact`。

```shell
snapcraft login
snapcraft register qwen3-embedding
make build
./dev/upload.sh latest/edge   # snapcraft upload <snap> --component ... --release=latest/edge
```

配置好 `SNAPCRAFT_STORE_CREDENTIALS` secret（`snapcraft export-login` 的输出）后，
`.github/workflows/cicd.yaml` 会在每次 push 到 `main` 时发布到 `latest/edge`。注意 CI
runner 需要约 25 GB 空闲磁盘：`make init-all` 会下载全部三个 GGUF，因为构建会将它们组织
为组件。
