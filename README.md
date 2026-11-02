# pixellogo

把一段标题 + 副标题 + 说明文字，渲染成 **8-bit / 复古终端风格**的像素图。
输出支持 PNG 与 SVG，内置小红书封面、4:3 横版、GitHub OG 预览图三种画布。

## 安装

```bash
pipx install git+https://github.com/sogeisetsu/pixel-logo-toolkit.git
```

## 使用

```bash
pixellogo -t "REA" -s "REVERSE ENGINEER" -d "One CLI for agents" -m xhs -o out/
```

## 文档

| 文件 | 内容 |
| --- | --- |
| [`docs/style-spec.md`](docs/style-spec.md) | 风格规格、不变式清单、提示词模板、配色方案 |
| [`docs/design.md`](docs/design.md) | CLI 设计与实现计划 |

## 开发

```bash
PYTHONPATH=src python -m pixellogo --version
PYTHONPATH=src python -m unittest discover -s tests -v
```

## 许可证

代码以 [MIT](LICENSE) 发布；字体各自遵循 SIL Open Font License 1.1，许可文本见 `src/pixellogo/assets/licenses/`。
