# 2026-11-21 12:18 — BookXray 初始架构与可审计基础版

## 变更内容

- 检查仓库：此前仅有 Apache-2.0 LICENSE，原许可证保留。
- 新建 Agent SKILL.md 和书籍分析、审计参考协议；支持中文/英文 README。
- 增加 Python 3.10+ CLI：prepare/audit/export，以及 EPUB、文本、可选 PDF 解析器。
- 新增 source hash、字符偏移、章节识别、连续文本工作包、证据校验和未覆盖章节阻断。
- 新增 JSON Schema、unittest 测试和 GitHub Actions CI。
- 新增架构、集成许可风险、评测计划、版本路线图文档。

## 已实现与未验证边界

- 已编写 deterministic pipeline 的代码和基础测试；提交时尚未取得 GitHub CI 运行结果。
- 真实 PDF/扫描教材、Docling 安装兼容性、OCR、公式图表、完整知识提取、语义自动评估均未完成真实样本验证。
- Agent 仍需根据工作包自己填写 units.json；程序不虚构模型已执行。
- PyMuPDF 的 AGPL/commercial licensing 需要单独审查；Apache-2.0 本项目许可证不覆盖其第三方权利。

## 下一步

1. 跟踪 CI 并修复测试缺陷。
2. 用获授权的真实 EPUB 和 PDF 构建黄金样本集，标注缺失章节和知识单元。
3. 加入可配置模型执行器、恢复机制和分层知识抽取。
4. 逐项引入 LangExtract、独立语义评价和精简证据面板；每次修改继续在 docs/routine 记录。
