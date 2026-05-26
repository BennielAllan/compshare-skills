# compshare-skills

Claude Code / Claude Agent SDK 的 skill 集合，用于 **CompShare（优云算力）** 与 **UCloud（优刻得）** OpenAPI 的文档查询与真实调用。

## 包含的 skill

| Skill | 用途 |
|-------|------|
| [`compshare-docs`](./compshare-docs) | 引导 AI 通过本地文档仓库回答 CompShare 平台问题（API / 操作指南 / 账户 / 模型服务），避免凭印象给出错误的 Action / 参数 / 步骤。文档源：[BennielAllan/compshare-docs](https://github.com/BennielAllan/compshare-docs)。 |
| [`ucloud-api-invoker`](./ucloud-api-invoker) | 通过本地 `invoker.py` 完成 UCloud / CompShare OpenAPI 的签名与 HTTP 调用，profile 路由到 `api.ucloud.cn` 或 `api.compshare.cn`。Action 与参数应来自 `compshare-docs` / `ucloud-api-docs` 的查询结果。 |

两个 skill 配合使用：先查文档 → 列必填参数 → 真实调用。写类操作（Create / Modify / Delete / Stop / Reboot / Terminate / Release）需用户明确确认后才执行。

## 安装

把对应目录拷贝到 Claude Code 的 skills 路径下即可，例如：

```bash
git clone https://github.com/BennielAllan/compshare-skills.git
cp -R compshare-skills/compshare-docs       ~/.claude/skills/
cp -R compshare-skills/ucloud-api-invoker   ~/.claude/skills/
```

或者作为 plugin 引用（取决于你的 Claude Code 版本与 marketplace 配置）。

## 凭证准备（仅 `ucloud-api-invoker` 需要）

`ucloud-api-invoker` 依赖 `~/.ucloud/config.json` 和 `~/.ucloud/credential.json`。首次使用时让 AI 运行：

```bash
python3 ~/.claude/skills/ucloud-api-invoker/scripts/setup_credentials.py \
  --profile <name> --platform <ucloud|compshare> \
  --public-key <pk> --private-key <sk> \
  [--project-id <pid>] [--active]
```

- PublicKey / PrivateKey 从对应控制台的 API 密钥页拿
- CompShare 场景不需要 ProjectID；UCloud 主账号可省，子账号必填
- `BaseURL` 由 `--platform` 决定，决定调用落到哪个 endpoint

## 关键安全规则

- **profile 必须显式传**：`ucloud-api-invoker` 用 profile 的 `BaseURL` 决定 endpoint。默认 profile 错配会导致请求落到错账号——HTTP 200 + RetCode 0 但数据是空或别人的。
- **实例 ID 平台歧义**：`uhost-xxx` 在 UCloud 标准 UHost 和 CompShare 两边格式相同。用户未提平台时必须反问。
- **写类操作二次确认**：`Terminate*` / `Delete*` / `Release*` / `Stop*` / `Reboot*` 等必须复述后果并等用户明确确认。

详见各 skill 目录下的 `SKILL.md`。
