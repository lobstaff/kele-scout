---
name: kele-scout
description: Use when the user sends a face selfie and wants to know which football (soccer) star they resemble, or asks for a "球星撞型 / 球星锐评 / 我像哪个球星" trading card. Produces a shareable football trading-card poster with a roast.
---

# Kele 球探 — 球星撞型锐评

把用户的一张自拍，变成一张可分享的「球星撞型」球员卡：判断他最像哪位足球明星，配一句毒舌锐评，渲染成 FIFA 风格球员卡发回去。

## 何时使用

- 用户发来一张**人脸自拍** + 表达"我像哪个球星 / 球星撞型 / 球探锐评 / 看看我像谁"。
- 仅在用户明确想玩撞型时触发；普通发图（传文件、问问题）**不要**触发。

## 安全红线（必须遵守）

1. **未成年人保护**：若照片主体是儿童/青少年，切换「快乐足球」友善模式——只夸不损，`tone=minor`，锐评全程鼓励、绝不评价外貌缺点。
2. **锐评红线**：可以毒舌、扎心、有梗，但**只吐槽气质/神态/反差/球风**；**绝不**碰长相缺陷、胖瘦、年龄、身材、种族、性别、长相美丑。
3. **隐私/版权**：卡面是 AI 生成的「神似致敬」形象，**不放用户真脸、不放真球星照片**。
4. **非人脸**：照片不是清晰人脸时，礼貌说明无法锐评，不要硬编。

## 流程（发图直接出整张卡）

你（gpt-5.5 agent）能直接看图。收到自拍后：

1. **看图判断**：① 是否未成年（是→`tone=minor`）② 撞型球星（必须具体名字，现役/退役均可，覆盖男足/女足/各国）③ 该球星的位置（中场/前锋/后卫/门将）④ 该球星的**视觉特征英文短语**（用于定向生成神似形象，如 `Asian female forward, ponytail, fierce confident`）⑤ 撞型指数 50-99 ⑥ 一句**中文锐评**（成人=毒舌守红线；未成年=友善鼓励）。
2. **调用脚本**生成球员卡：
   ```bash
   python3 skills/kele-scout/generate_card.py \
     --star "王霜" --position "中场" --match 72 \
     --features "Asian female football forward, ponytail, fierce confident expression" \
     --ruping "笑得像来交朋友，上场把对手防线拆到报警——典型笑面收割机。" \
     --tone adult
   ```
   - 脚本读环境里的 keleclaw 凭据，自动调 gpt-image-2 出卡面 + 合成文字 + 渲染中文。
   - 成功后脚本在最后一行打印卡片图的**绝对路径**。
3. **发图回用户**：在你的回复里输出一行 `MEDIA:<脚本打印的绝对路径>`，Hermes 会把卡片图发给用户。同时可附一句简短的口语版锐评。

## 参数说明

| 参数 | 必填 | 说明 |
|---|---|---|
| `--star` | 是 | 撞型球星中文名 |
| `--position` | 是 | 位置（中场/前锋/后卫/门将） |
| `--match` | 是 | 撞型指数 50-99 |
| `--features` | 是 | 球星视觉特征英文短语（定向生成神似形象用，描述气质不照搬身份） |
| `--ruping` | 是 | 一句中文锐评（≤40 字最佳，会印在卡上） |
| `--tone` | 否 | `adult`(默认) / `minor`(友善模式，卡面也会用阳光青春风) |

## 失败兜底

- gpt-image-2 偶发限流（org 级共享），脚本已内置重试；若最终仍失败，脚本退出非零并打印原因——这时**先把文字锐评发给用户**，告诉他"球员卡稍后重试一下"。
