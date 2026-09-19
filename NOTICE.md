# 第三方声明

本文件是补充说明，**不是许可证**。本项目的许可证是 [MIT](LICENSE)。

## Optiland

本项目汉化的对象是 [Optiland](https://github.com/optiland/optiland) 的图形界面。

```
MIT License
Copyright (c) 2024 Kramer Harrison
```

项目主页：<https://github.com/optiland/optiland>

### 本项目与 Optiland 的关系

`optiland-zh` **不分发、不修改、也不链接** Optiland 的源码。它的工作方式是
在用户自己的进程里，于运行期给 PySide6 的绑定方法重新赋值，从而在文字进入
Qt 之前把它替换掉。

本仓库只包含自己的源代码和翻译数据。Optiland 是运行期依赖，需要单独安装：

```sh
pip install "optiland[gui]"
```

## PySide6 / Qt

本项目的汉化层依赖 PySide6 提供的 Qt 绑定，并在运行期加载 PySide6 自带的
Qt 翻译文件（`qtbase_zh_CN.qm`）来覆盖 Qt 内置的文字（对话框按钮、
文件选择器的标签等）。

PySide6 由 Qt 公司及其贡献者提供，采用 LGPL v3 / 商业双许可。
本项目不打包、不修改这些文件，只是在运行期引用它们。

## 术语参考

词库里的中文术语对齐 Zemax OpticStudio 中文版的习惯用法（Lens Data Editor →
镜头数据编辑器、Aperture → 孔径、Spot Diagram → 点列图 等）。

这里只是术语惯例的参考，不涉及任何 Zemax 的代码、数据或文件格式实现。
