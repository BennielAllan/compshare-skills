---
name: compshare-docs
description: 当用户明确提及 CompShare / 优云算力 / 算力共享平台 / api.compshare.cn 或询问 CompShare 平台的具体 API、GPU 实例操作、镜像、账户账单、模型服务（modelverse）等问题时使用。覆盖 CompShare 全部产品文档（API/操作指南/账户/模型服务/概览/协议）。普通 UCloud 产品（UHost/ULB/UDB 等非 CompShare）的问题不触发；用户已知 Action 想真实调用时也不触发（走 ucloud-api-invoker）。
---

# CompShare（优云算力）文档查询

引导 AI 通过本地文档仓库回答 CompShare 问题，避免凭印象给出错误的 Action / 参数 / 步骤。

## 第 0 步：同步文档仓库

执行前先告知用户"正在同步 CompShare 文档"，再跑下面这段 bash（**一字不变**）：

```bash
REPO=/tmp/compshare-docs
STAMP=$REPO/.last_pull
if [ ! -d "$REPO" ]; then
  git clone --depth 1 https://github.com/BennielAllan/compshare-docs.git "$REPO" && touch "$STAMP"
elif [ ! -f "$STAMP" ] || [ $(($(date +%s) - $(stat -f %m "$STAMP" 2>/dev/null || stat -c %Y "$STAMP"))) -gt 86400 ]; then
  git -C "$REPO" pull --ff-only && touch "$STAMP"
else
  echo "compshare-docs is fresh, skip pull."
fi
```

- 仓库公开在 GitHub，无需 VPN
- 失败时执行 `rm -rf /tmp/compshare-docs` 后**重跑整段 bash**
- 仍失败 → 转"失败处理"，禁止凭记忆作答

## 第 1 步：归类

读 `/tmp/compshare-docs/pages/_meta.json`，按下表确定一级目录：

| 用户意图 | 目录 |
|---------|------|
| API / 接口 / Action 名 | `gpus/` |
| 创建/登录/磁盘/防火墙/镜像/计费 操作 | `operation/` |
| 账号 / 账单 / 团队管理 | `uaccount/` |
| 模型 API 服务（modelverse） | `modelverse/` |
| 平台介绍 / 产品概念 / 会员 | `overview/` |
| 服务协议 / SLA | `serviceagreement/` |

- `console` 是外链，跳过
- 概念性问题（如"有几种镜像类型"）优先 `operation/`，API 细节在 `gpus/`，必要时两边都看

## 第 2 步：定位文件

读 `pages/<category>/_meta.json`：

- 键是叶子文件 → 直接 Read `<key>.md(x)`
- 键是子目录 → 再读一层 `_meta.json`

**API 文档键命名规律**：`gpus/<sub>/<key>.md` 的 `<key>` 全小写 ↔ ActionName PascalCase。如 `createcompshareinstance` ↔ `CreateCompShareInstance`。

**典型路径速查**（命中后直接 Read，不要 `ls` 验证）：

| 用户问题 | 路径 |
|---------|------|
| 创建 GPU 实例 API | `gpus/instance/createcompshareinstance.md` |
| 列实例 / 查实例 API | `gpus/instance/describecompshareinstance.md` |
| 可用机型规格 API | `gpus/instance/describeavailablecompshareinstancetypes.md` |
| 可用区列表 API | `gpus/instance/describecomparesupportzone.md` |
| 错误码 | `gpus/compshareerrorcode.md` |
| API 接口范例 | `gpus/operationexample.md` |
| 怎么登录实例 | `operation/gpu/logininstance.md` |
| 怎么创建实例（控制台） | `operation/gpu/createresources.md` |
| 抢占式实例 | `operation/gpuspot/gpuspot.md` |
| 镜像类型概念 | `operation/image/imagecommunity.md` |

候选多于 1 个 → 列 2-3 条让用户选；**不要**用 `ls -p` 验证存在性，先 Read 失败再退回 `ls`。

## 第 3 步：读文件提取

### API 文档（`gpus/<sub>/<action>.md`）
按顺序看：标题取 ActionName → 接口说明 / 使用限制 → 请求参数表（名称/类型/必填）→ GPU 类型列表（如有）→ 响应参数 → 请求/响应示例。

### 操作指南（`operation/`）
按 `##` 小节复述。截图链接不必复述 URL，说"详见控制台截图"。

### 多 Action 候选的歧义（重要）
"看看我的镜像" "查我的实例" 这类口语化请求，可能对应多个 Action（如镜像查询有 6 个：`DescribeCompShareImages / DescribeCompShareCustomImages / DescribeFavoriteImages / DescribeSelfCommunityImages / DescribeCompShareSharingImages / DescribeCommunityImages`）。

**禁止瞎挑一个**。先列候选反问：

> "镜像查询有多种，你想看：
> A) 我自己制作的镜像（Custom）
> B) 我收藏的镜像（Favorite）
> C) 我发布到社区的镜像（SelfCommunity）
> D) 别人共享给我的镜像（Sharing）
> E) 平台官方镜像（System/App）"

## 反幻觉规则

1. **Action 名、参数名、字段值必须来自实际读过的文档**
2. **文档里没有的硬约束**（GPU 型号、CPU/内存合法组合、磁盘类型限制）说"文档里没有"，不要编线性规律
3. **文档说"通过 XxxAction API 查询"** 的精确值（如 V100S 各卡数 CPU/Memory 合法组合需调 `DescribeAvailableCompShareInstanceTypes`）→ 引导用户调 API，不要从表头最大值反推
4. **响应示例中的可用区/规格数据** 是历史快照，不是当前实时值——明确告诉用户"这是示例，实时数据需调 API"
5. **同步失败时禁止凭记忆作答**

## 与 ucloud-api-invoker 的衔接

| 用户意图 | 衔接方式 |
|---------|---------|
| 只问文档 / 概念 / 参数 | 仅本 skill，不调 invoker |
| **读类操作**（"列一下我的实例"、"查 xxx 详情"）| **自动**串联：查文档 → 调 invoker（用 CompShare profile）→ 展示结果。无需用户中间确认 |
| **写类操作**（Create / Modify / Stop / Reboot / Reset / Terminate / Delete / Release）| 查文档 → 列必填参数 → 复述要做的事 → **等用户明确确认**才调 invoker |

**实例 ID 歧义**：`uhost-xxx` 在 UCloud 标准 UHost 和 CompShare 两边格式相同。若用户没说明平台但提供了 `uhost-xxx`，**必须反问**或按上下文（用户提了 CompShare/优云算力等关键词）判断。**不要凭格式猜测，会拿到错账号的数据**。

## 失败处理

**仓库同步失败**：
```
同步 CompShare 文档失败：<错误>
仓库：https://github.com/BennielAllan/compshare-docs.git
请确认网络可达 github.com，或手动克隆到 /tmp/compshare-docs。
在同步成功前我不会凭记忆作答。
```

**目标文件找不到**：
```
已同步文档，但在 pages/<category>/ 下没找到 "<关键词>" 相关条目。
可选：(A) 我换其他类目搜 (B) 列出 <category> 下所有条目让你挑 (C) 你描述要做的操作，我帮你匹配 Action。
```

**文件读到但内容缺失目标项**（如"错误码 230"不在错误码表中）：
```
文档收录的<X>是 <列出文档里有的项>，没有 "<用户问的>" 这一条。
可能：(1) 文档未收录该项 (2) 是平台/网关层的非业务码。建议联系技术支持或检查上下文。
```
