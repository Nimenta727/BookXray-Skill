# 2026-11-21 12:30 — 第一轮 CI 问题修复

## 实测结果

首次 GitHub Actions 工作流运行 #44866362713：安装、compileall 成功；6 个 unittest 中 5 个通过、1 个报错。EPUB XHTML 标题解析出现 Python 类型错误：字符串 tag[1] 不能直接作为字符串重复倍数。错误发生在 bookxray/core.py 的 XHTMLText.handle_starttag。

## 本次修改

- 将标题层级转换为整数 int(tag[1])，避免 EPUB 章节解析失败。
- 维持原有 test_epub_spine_order 回归用例，后续 CI 必须验证该用例通过。
- 更新 pyproject.toml 的 SPDX license 声明，适配新版 setuptools，修复弃用告警。
- GitHub Actions 升级到 checkout v5 和 setup-python v6，以适应 Node 24。

## 下一步

1. 复查本次 GitHub Actions CI 是否全部通过；失败则定位并修正。
2. 使用真实授权书籍进行 EPUB/PDF/复杂版面测试，不用合成测试替代真实性能。
3. 加强章节识别、断点恢复、语义审查及结构化知识单元生成。
