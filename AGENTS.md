# Reproduction4grade1 论文复现规则

本文件适用于仓库根目录及全部 `projects/` 子目录；更近的 `AGENTS.md` 可补充或覆盖本规则。

## 固定入口

- 本仓库是所有论文复现代码的固定仓库；每篇论文代码放在 `projects/<paper-id>/`，不要再询问 GitHub 仓库地址。
- 论文阅读或复现任务开始时，先读取 `C:\Users\16682\Desktop\读研工具\论文复现工作流_v2.md` 并按其当前版本执行。只有维护工作流本身时才需要读取 `论文复现工作流_修改建议.md`。
- 编辑知识库前，读取 `E:\github-local-repository\recsys-firstgrade\AGENTS.md` 及目标目录附近的 README。
- 普通 Markdown 文件不会因存在而自动成为授权；实验范围、预算和远程执行仍以用户批准的 `实验复现.md` 为准。

## 双仓库职责

- 代码、配置、测试、运行清单和小型结果摘要：`Reproduction4grade1/projects/<paper-id>/`。
- 论文、`Note.md`、`实验复现.md`、`STATUS.md`、`复现结果.md`：`E:\github-local-repository\recsys-firstgrade\knowledge_base\paper\<topic>\<paper-id>\`。
- 项目 README 必须反向链接知识库文档；知识库记录本仓库 URL、项目路径、分支、实验 commit 和上游 commit。
- 外部官方代码仅作为 upstream；导入时不保留嵌套 `.git`，并在 `UPSTREAM.md` 记录来源、commit/tag、许可和导入方式。

## 实验与交付

- 先解释论文完整实验地图，再由用户选择基础实验和创新实验；统一写入 `实验复现.md` 并获批后才执行。
- 正式任务启动后，在 `实验复现.md` 写明用户可直接复制的进程、GPU、日志、状态、退出码、checkpoint 和汇总查看方法，并使用真实批次路径。
- 实验完成后必须生成结构清晰的 `复现结果.md`：区分基础/创新实验，包含可追溯数据、必要图表、误差与原因分析、改进方向和可迁移学习。
- 数据集、大 checkpoint、原始日志、缓存和凭据不得提交 GitHub；只版本化脚本、配置、manifest、指标摘要、表格/小图和分析报告。
- AutoDL 实例按论文独立绑定；密码、私钥、token、Cookie 和验证码不得进入仓库、文档、日志或命令历史。

## 改动与验证

- 默认中文说明；只修改任务直接涉及的内容，保护已有改动。
- 使用相对路径、显式随机种子和可复核命令；结束前执行与改动范围匹配的最小验证并检查文档链接。
