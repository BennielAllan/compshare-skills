# compshare-skills

## 包含的 skill

| Skill | 用途 |
|-------|------|
| [`compshare-docs`](./compshare-docs) | 引导 AI 通过本地文档仓库回答 CompShare 平台问题（API / 操作指南 / 账户 / 模型服务），避免凭印象给出错误的 Action / 参数 / 步骤。文档源：[BennielAllan/compshare-docs](https://github.com/BennielAllan/compshare-docs)。 |
| [`ucloud-api-invoker`](./ucloud-api-invoker) | 通过本地 `invoker.py` 完成 UCloud / CompShare OpenAPI 的签名与 HTTP 调用，profile 路由到 `api.ucloud.cn` 或 `api.compshare.cn`。Action 与参数应来自 `compshare-docs` / `ucloud-api-docs` 的查询结果。 |

## 安装

先克隆本仓库：

```bash
git clone https://github.com/BennielAllan/compshare-skills.git
cd compshare-skills
```

### Claude Code

```bash
# 全局（推荐）
mkdir -p ~/.claude/skills
cp -R compshare-docs ucloud-api-invoker ~/.claude/skills/

# 或项目级
mkdir -p .claude/skills
cp -R compshare-docs ucloud-api-invoker .claude/skills/
```

### Cursor

Cursor 2.4+ 原生支持 `SKILL.md` 格式，会从 `~/.cursor/skills/`、`.cursor/skills/` 自动加载，也兼容 `~/.claude/skills/`。

```bash
# 全局
mkdir -p ~/.cursor/skills
cp -R compshare-docs ucloud-api-invoker ~/.cursor/skills/

# 或项目级
mkdir -p .cursor/skills
cp -R compshare-docs ucloud-api-invoker .cursor/skills/
```

### Codex CLI

```bash
# 全局
mkdir -p ~/.codex/skills
cp -R compshare-docs ucloud-api-invoker ~/.codex/skills/

# 或项目级
mkdir -p .agents/skills
cp -R compshare-docs ucloud-api-invoker .agents/skills/
```

安装完后**重启 Codex** 才会加载新 skill。
