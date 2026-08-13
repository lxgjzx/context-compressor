# Context Compressor 上下文压缩

一个**与 agent 框架无关**的上下文压缩 skill,用于压缩 agent 的对话上下文、会话记录和工作笔记,在长会话中节省 token、避免上下文窗口溢出。

适用于 **Claude Code、Codex、Cursor、Windsurf、OpenSquilla**,以及任何能读 Markdown、能跑 Python 3(纯标准库)的 agent。

> English: [README](README.md)

## 为什么需要它

长会话会积累大量噪声:重复执行的命令、重复的工具输出、ANSI 转义符、base64 数据块、样板文案、以及已解决的讨论。Context Compressor 提供:

- 清晰的**何时压缩**策略(上下文 ≥70%、超过 30 轮、阶段完成、派生子 agent 前……)
- 一个 5 步**工作流**:盘点 → 选策略 → 压缩 → 校验 → 汇报
- 一份**"绝不能丢"清单**:当前目标、约束、决策、待办、精确报错字符串、环境坑
- 一个**纯标准库 Python 工具**(`scripts/compress.py`)负责机械部分

## 安装

把整个文件夹复制到你的 agent 的 skills/rules 目录:

| Agent | 路径 |
|---|---|
| Claude Code | `~/.claude/skills/context-compressor/`(个人)或 `.claude/skills/context-compressor/`(项目) |
| Codex | `.agents/skills/context-compressor/`(见 `AGENTS.md`) |
| Cursor | `.cursor/rules/context-compressor.mdc`(或引用该文件夹) |
| Windsurf | `.windsurf/rules/context-compressor.md` |
| OpenSquilla | `skills/context-compressor/`(工作区) |

完整的兼容性映射和移植方法见 `references/agents.md`。

## 命令行用法

```bash
# 估算 token 数
python3 scripts/compress.py count transcript.md
python3 scripts/compress.py report logs/*.md     # 前后对比表

# 机械压缩(加 --dry-run 可预览而不写入)
python3 scripts/compress.py strip transcript.md
python3 scripts/compress.py dedup transcript.md
python3 scripts/compress.py truncate transcript.md --keep-head 20 --keep-tail 15
```

token 估算优先使用 `tiktoken`(装了的话,`pip install tiktoken`),否则用一套支持中日韩字符的启发式算法(约 1 个 CJK 字符 = 1 token,其余约 4 字符 = 1 token)。

## 效果示例

一段 715 行、约 20.5k token、充满重试和噪声的会话记录:

| 阶段 | token | 相比原始 |
|---|---|---|
| 原始 | 20,513 | — |
| `strip`(去噪) | 18,173 | −11% |
| `dedup`(去重) | 12,314 | −40% |
| `truncate`(滚动窗口) | 759 | **−96%** |

在此基础上,`SKILL.md` 工作流里的**语义摘要**还能进一步压缩。

## 目录结构

```
SKILL.md                 # 触发条件 + 5 步工作流 + 绝不能丢清单
scripts/compress.py      # 纯标准库 CLI(count / report / strip / dedup / truncate)
references/strategies.md # 压缩策略库
references/agents.md     # 各 agent 安装映射 + 兼容性说明
tests/                   # 单元测试
```

## 测试

```bash
python3 -m unittest discover -s tests -v
```

GitHub Actions 会在 Python 3.9 / 3.11 / 3.13 上自动运行这些测试。

## License

MIT
