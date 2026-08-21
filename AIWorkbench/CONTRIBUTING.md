# 贡献指南

感谢你对 AIWorkbench 的关注！我们欢迎任何形式的贡献。

## 如何贡献

1. **报告 Bug**：新建 Issue，描述复现步骤、期望行为与实际行为。
2. **提需求**：新建 Issue，说明使用场景。
3. **提交代码**：Fork 仓库 → 创建分支 → 提交 → 发起 Pull Request。

## 代码风格

- Python 3.10+
- 遵循 [PEP 8](https://peps.python.org/pep-0008/)，4 空格缩进。
- 中文注释与文档，保持一致。

## 提交前检查

```bash
pip install -r requirements.txt
python -m py_compile app/*.py app/ui/*.py
python main.py
```

## Pull Request 流程

1. 在 PR 描述中清晰说明改动目的与内容。
2. 尽量保持一个 PR 只解决一个问题。
3. 确保现有功能不被破坏。

## 许可证

提交代码即表示你同意将其以 [Apache License 2.0](LICENSE) 授权。