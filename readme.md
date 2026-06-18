# 104-107

## cursor agent 四种模式

## Agent模式
已有确定的需求文档和设计

## Plan 模式

### 面对陌生领域的建议
建议在确定需求、技术方案的前提下使用
1. 借助chatgpt、gemini进行深度调研（deeprearch），生成技术方案
2. 将调研好的技术方案结合cursor的plan模式生成执行计划

### 使用示例
正确：帮我解读当前项目的源码，我需要在当前项目里实现一个接入钉钉的功能，我该怎么做
错误：我需要实现一个接入钉钉的功能，我该怎么做

## mdc与md文件的区别

### .md —— 普通 Markdown 文档

用途：给人读的说明文档，如 README.md、CHANGELOG.md、架构说明等。
位置：项目任意位置均可。
Cursor 处理：Cursor 不会自动把它注入到 AI 上下文中（除非你手动 @ 引用它）。
格式：纯 Markdown，无特殊元数据。

### mdc —— Cursor 项目规则文件（Project Rules）

用途：给 Cursor AI Agent 看的持久指令/编码规范，会自动注入到模型上下文中。
位置：必须放在项目根目录下的 .cursor/rules/目录内（如 .cursor/rules/react-style.mdc）。
Cursor 处理：.cursor/rules/下的 .mdc文件会被规则系统扫描并按条件自动注入 AI 上下文；同目录下放的 .md文件会被忽略。
格式：Markdown + YAML Frontmatter（头部用 ---包裹元数据）

典型结构

```md
---
description: React 组件编码规范
globs: ["src/**/*.tsx"]
alwaysApply: false
---
# 规则正文
- 使用 function 声明组件，不用箭头函数
- Props 必须写 interface
```