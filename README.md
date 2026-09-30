# Reproduction4grade1

本仓库统一管理论文复现代码。论文原文、阅读笔记、实验计划和状态文件保存在 `recsys-firstgrade` 知识库中；本仓库只保存可运行代码、配置、测试、运行清单和小型结果摘要。

## 固定目录

```text
projects/<paper-id>/
  README.md
  UPSTREAM.md
  <官方代码或自行实现>
  configs/
  scripts/
  repro/runs/
  results/summary/
```

数据集、checkpoint、原始日志及大型实验产物不进入 Git。

## 新项目

1. 在 `projects/<paper-id>/` 建立唯一项目目录。
2. 外部官方代码只作为 upstream；导入前记录 URL、commit/tag、许可和日期，不保留嵌套 `.git`。
3. 在项目 README 中链接对应知识库目录：`../recsys-firstgrade/knowledge_base/paper/<topic>/<paper-id>/`。
4. 先固定数据与评估协议，再执行最小测试和正式训练。

完整流程见：`C:\Users\16682\Desktop\读研工具\论文复现工作流_v2.md`。

## 项目索引

新建项目时在此追加：论文简称、代码目录、知识库目录、upstream commit 和当前状态。

- **SimDiffRec**
  - 代码：[`projects/SimDiffRec/`](projects/SimDiffRec/)
  - 知识库：[`recsys-firstgrade/knowledge_base/paper/diffusion/SimDiffRec/`](../recsys-firstgrade/knowledge_base/paper/diffusion/SimDiffRec/)
  - upstream：`zingyon/SimDiffRec@eb6784b2e9741052c5f104847e41b5accc812e7e`
  - 状态：阅读与静态代码审计完成，尚未下载数据或启动训练
