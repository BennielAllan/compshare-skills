---
name: ucloud-api-invoker
description: 当用户**明确提及 UCloud（优刻得）或其子平台 CompShare（优云算力 / 优云智算）**且想**真实执行/调用/run** API 时使用（例如"帮我列一下 cn-bj2 的 UHost 主机"、"用 UCloud API 删除 ULB xxx"、"CompShare 帮我创建 V100S 主机"、"优云智算上列一下我的实例"）。本 skill 调用本地 invoker.py 脚本完成签名和 HTTP 请求；通过 profile 的 `BaseURL` 路由到 api.ucloud.cn 或 api.compshare.cn。Action 和参数应来自 `ucloud-api-docs`（UCloud 标准产品）或 `compshare-docs`（CompShare 平台）skill 的查询结果，不要凭印象。仅"查文档"不触发本 skill。
---

# UCloud API 真实调用

通过本地 invoker.py 执行 UCloud / CompShare OpenAPI。先用 `ucloud-api-docs` 或 `compshare-docs` 查清 Action 和参数，再来调用。

## 调用前必查清单

1. **凭证存在**：`ls ~/.ucloud/config.json ~/.ucloud/credential.json`。缺失则补全：
   - 询问用户索取 **PublicKey** 和 **PrivateKey**（让用户从对应平台控制台 API 密钥页拿）
   - **ProjectID**：CompShare 场景**不问不传**；UCloud 场景询问（**主账号可省，子账号必填**）
   - 跑脚本写入：
     ```bash
     python3 ~/.claude/skills/ucloud-api-invoker/scripts/setup_credentials.py \
       --profile <name> --platform <ucloud|compshare> \
       --public-key <pk> --private-key <sk> \
       [--project-id <pid>] [--active]
     ```
   - 脚本输出 `{"ok": true, ...}` 即成功；`{"ok": false, "error": "..."}` 则把错误原样告诉用户
   - **凭证字段不准编造**，用户拒绝提供 → 终止本次调用
2. **invoker.py 存在**：`~/.claude/skills/ucloud-api-invoker/scripts/invoker.py`
3. **Action 已确定**：来自 `ucloud-api-docs` 或 `compshare-docs`。**每个 API 的必填字段不同，以文档为准**
4. **按文档必填项检查参数**：对照文档"请求参数"表，逐项确认必填字段（`Required=Yes`）是否已知。处理规则：
   - **必填且用户已提供** → 直接用
   - **必填但用户没说** → 优先反问。仅当文档明确给出默认值（如 `MachineType=G`）才可用默认
   - **非必填** → 用户没说就**不传**，让服务端用默认行为
   - **写操作（Create/Modify/Delete...）的危险参数**（如销毁时的 `ReleaseEIP`/`ReleaseUDisk`）即便非必填也应主动列出让用户选
   - **不要 Describe 搜索去猜未知参数**（如不知道实例 ID 就反问，不要列实例让用户对号入座）

## 调用模板

```bash
echo '{"action":"<ActionName>","params":{...},"profile":"<profile_name>"}' \
  | python3 ~/.claude/skills/ucloud-api-invoker/scripts/invoker.py
```

- `action` PascalCase
- `params` 业务参数字典——**所有 value 都是字符串**（包括数字 `"10"`、布尔 `"true"`/`"false"`、整数化浮点 `"42"`）
- `profile` 见下节，**强烈建议每次显式传**
- 不传 `Action / PublicKey / Signature`，invoker 自动加

输出：stdout 单行 JSON（`ok=true/false`），stderr 是人类日志（用 `2>/dev/null` 抑制）

## ⚠ profile 必须显式传（重要安全规则）

invoker 用 profile 的 `BaseURL` 决定 endpoint。**默认 profile 错配 endpoint 会导致请求落到错账号——HTTP 200 + RetCode 0 但数据是空或别人的**，最隐蔽的坑。

| 场景 | profile 选择 |
|------|-------------|
| UCloud 标准产品（UHost / ULB / UDB / UFile / VPC / UK8S 等） | `BaseURL=https://api.ucloud.cn` 的 profile |
| CompShare / 优云算力 / 优云智算 / Action 名带 `CompShare` | `BaseURL=https://api.compshare.cn/` 的 profile |

**判断 CompShare 场景**：用户说了 `CompShare / 优云算力 / 优云智算 / 算力共享 / compshare.cn`，或 Action 含 `CompShare`，或上一步走过 `compshare-docs`。

**首次调用前，查一下用户有哪些 profile**：
```bash
cat ~/.ucloud/config.json | python3 -c "import json,sys; [print(p.get('Profile'), '→', p.get('BaseURL','https://api.ucloud.cn')) for p in json.load(sys.stdin)]"
```

按 BaseURL 挑对的 profile 名，显式传 `"profile": "<name>"`。**没有匹配的 profile 就告诉用户去加，不要凑合用错的**。

## 实例 ID 平台歧义

`uhost-xxx` 格式在 UCloud 标准 UHost 和 CompShare **两边通用**。仅凭 ID 无法判断平台。

- 用户给了 `uhost-xxx` 但**未提平台关键词**（CompShare / 优云算力 / UHost / UCloud）→ **必须反问**：
  > "这台机器是 UCloud 标准 UHost 还是 CompShare（优云算力）的实例？两边 ID 格式一样，我得确认才能选对 endpoint。"
- 错选 endpoint 不会立刻报错，会返回空集或别人的数据，**事后很难发现**

## 参数构造

- **字符串**：所有 value 都是 string——数字 `"10"`、布尔 `"true"`、浮点 `"42"`（小数部分为 0 时去掉小数点；非 0 时按 `"3.14"` 传）
- **数组**：点号下标平铺，如 `"Disks.0.IsBoot": "True"`、`"Disks.0.Size": "40"`、`"Disks.1.Type": "CLOUD_SSD"`
- **ProjectId**：profile 里有 `ProjectID` 字段则 invoker 自动注入；params 里显式传则以 params 为准
- **Region / Zone 等业务参数**：按 API 文档传，invoker 不自动注入

## 危险操作二次确认

调用前**必须**主动复述并等用户明确确认才执行的 Action：

- **销毁类**：`Terminate*` / `Delete*` / `Release*` / `Remove*`（资源不可恢复）
- **中断业务类**：`Stop*` / `PowerOff*` / `Shutdown*` / `Reboot*` / `Reset*`（业务中断）
- **配置变更类**：`Modify*Network*` / `Modify*Security*` / `Modify*Bandwidth*` / `Resize*`（可能切流量或重启）
- **批量操作**：一次调用影响多个资源

**复述模板**：
> "我即将执行 **<Action>**，参数：`<关键参数>`。后果：**<具体后果>**。
> 确认要执行吗？"

**具体后果**示例：
- Terminate：销毁实例 uhost-xxx，数据不可恢复（除非启用了回收站）
- Reboot：重启实例 uhost-xxx，中断当前业务约 1-2 分钟
- Stop：关机 uhost-xxx，业务停止；数据保留，可后续 Start
- ResetPassword：重置 uhost-xxx 的密码

**密码 / 密钥参数额外安全**：
- 复述时**不要回显**密码明文，写成"已收到密码（不在此显示）"
- 提示用户：密码会通过命令行传给 invoker，**会出现在 shell 历史和 invoker stderr 日志**。敏感场景建议操作完后清理 `~/.zsh_history` / `~/.bash_history`

**销毁实例时的连带参数**：
Terminate 类带 `ReleaseEIP` / `ReleaseUDisk` 等可选参数，影响 EIP 是否释放、数据盘是否一起销毁。复述时**主动列出**让用户选，不要默认。

读类（`Describe*` / `Get*` / `List*` / `Check*`）无需复述，可直接执行。

## 输出处理

```json
{"ok": true, "http_status": 200, "response": {"RetCode": 0, ...}}
```
取 `response`，按文档字段说明转述。响应里的 `Password` / `FileBrowserPassword` / `PrivateKey` 等**敏感字段不要直接打印给用户**，提示"密码字段已隐藏，需要可单独索取"。

```json
{"ok": false, "error_class": "...", "message": "...", "ret_code": 123}
```

| error_class | 处理 |
|------------|------|
| `config_error` | 凭证或 profile 名不对，让用户检查 `~/.ucloud/` 和 `profile` 参数 |
| `network_error` | 网络问题，可重试 1 次 |
| `signing_error` | params 里有非字符串值，**这是 AI 的 bug**，检查后改正重试 1 次 |
| `api_error` | UCloud 返回了 RetCode 非 0，按 `message` 转述。常见：`170`(签名/凭证错) `230`(参数错) `200`(权限不足) |

失败后**不要凭记忆改参数重试**，回 `*-docs` skill 重读文档。

## 反模式（别犯）

- ❌ 不查文档凭印象编 Action 名 → 大概率 RetCode != 0
- ❌ params 传数字/布尔字面值（`"Limit": 10`）→ signing_error
- ❌ 文档必填字段缺失时自己填默认值（除非文档明确给出默认值）→ 拿到错数据或操作错资源
- ❌ 文档非必填字段也强行传值 → 可能覆盖服务端合理默认
- ❌ 不显式传 profile → 落到错 endpoint，返回错账号数据
- ❌ Stop/Terminate 类不复述就直接调
- ❌ 调用失败后改个参数硬试 → 回文档查清楚再来
