[English](README.md) | [中文](README.zh-CN.md)

# Kele 球探 · 球星撞型锐评卡

一个 [Hermes](https://github.com/lobstaff) agent skill:发一张自拍，助手告诉你
最像哪位**足球明星**，配一句毒舌锐评，渲染成一张 **FIFA 风格球员卡**直接发回对话。

## 它能做什么

1. 你给助手发一张人脸自拍，说"球星撞型 / 我像哪个球星"。
2. 助手（gpt-5.5 多模态）看图判断：撞型球星、位置、气质、撞型指数、一句锐评。
3. `generate_card.py` 调 `gpt-image-2` 画一张**神似致敬**卡面（一个气质相符的
   通用形象——不是球星本人照片，也不是你的真脸），再用思源黑体叠上文字。
4. 成品球员卡直接发回给你。

## 安装

直接对你的助手说：

> 帮我安装球星撞型

助手会用 Hermes 原生 skill 管理器，把本仓库注册为 skill 源并安装：

```
hermes skills tap add lobstaff/kele-scout
hermes skills install kele-scout
```

安装到助手自己的 skill 目录（存在持久卷上）——**按需安装、每个助手独立开通、
不烤进基础镜像**。

## 工作原理

- `SKILL.md` —— 助手读取的指令（何时触发、安全红线、流程）。
- `generate_card.py` —— 渲染器：`gpt-image-2` 出卡面 + PIL 叠文字。思源黑体
  首次运行自动下载缓存。

## 安全

- **未成年人**：若主体像儿童/青少年，自动切换温暖鼓励模式——只夸不损，绝不
  锐评外貌。
- **锐评红线**：只吐槽气质 / 神态 / 球风，**绝不**碰真实长相、身材、年龄、
  种族、性别。
- **隐私与肖像**：卡面用 AI 生成的神似致敬形象——不放你的真脸，也不放真球星照片。

## 运行依赖

在 Hermes pod 内运行，环境里需有 keleclaw 推理凭据
（`OPENAI_API_KEY` / `OPENAI_BASE_URL`）+ Python 3 + Pillow。
