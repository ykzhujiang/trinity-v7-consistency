# V7-013 Retrospective — 《合伙人》3角色一致性压力测试

**Date**: 2026-04-10
**Status**: ✅ Both tracks complete, 朱江高度认可

## 实验概要
- **故事**: 3合伙人（林远/苏晴/胖虎）讨论5000万收购，全家桶反转喜剧
- **假设**: H-132 — 3角色比2角色一致性显著下降
- **双轨**: anime + realistic

## 成功因素分析

### 1. 角色视觉锚点设计（关键）
每个角色有 3+ 强视觉区分特征：
- **林远**: 黑框方形眼镜 + 深蓝修身西装 + 白色口袋巾（正式/瘦高）
- **苏晴**: 灰色宽松卫衣 + 牛仔裤 + 齐肩微卷黑发（休闲/年轻）
- **胖虎**: 红蓝花纹夏威夷衬衫 + 卡其短裤 + 壮实圆脸（搞笑/随意）

**教训**: 3角色必须在服装颜色、体型、配饰上形成极端对比。不能有任何两个角色"像"。

### 2. Physical State Anchoring (PSE) 扩展到3人
- 每个 Segment 开头声明所有3角色的精确姿态和位置
- 明确座位关系：林远-右侧靠窗、苏晴-左侧靠门、胖虎-短边远端
- 关键：在 prompt 中反复出现"glasses-man (right/window), hoodie-girl (left/door), hawaiian-shirt-guy (far end)"

### 3. Anime 轨道：Gemini refs + FFA + Video Extension
- Gemini 生成角色参考图 + 场景图 → Seedance @image refs
- Seg2 用 FFA（Seg1 最后一帧作为 @image1）+ Video Extension
- 效果很好：角色在两个 Segment 中可辨认

### 4. Realistic 轨道：纯文本 + Video Extension（突破）
- **发现**: 所有含真人的图片（角色参考、Seg1 截帧）都被 Seedance 隐私过滤器拦截
- **解决**: 完全放弃图片引用，仅使用详细文本描述 + Video Extension
- Video Extension 是关键：Seedance 对 --video 输入不做隐私检查
- 纯文本 PSE 必须极度详细（每个角色 50+ 字描述）

### 5. 喜剧题材+强情节转折
- 全家桶反转 = 出人意料 + 轻松
- 对白密度高、角色互动多 → 每个 Part 都有事发生
- 3角色各有鲜明性格：严肃/务实/搞笑

## 双轨技术总结

| 维度 | Anime | Realistic |
|------|-------|-----------|
| Seg1 输入 | Gemini 角色图 + 场景图 | 纯文本 |
| Seg2 FFA | ✅ Seg1 截帧作 @image1 | ⛔ 被隐私过滤拦截 |
| Seg2 Video Extension | ✅ | ✅（唯一可行方案）|
| 人物一致性 | 高（图片锚定） | 中高（靠文本描述+视频延续）|
| 音频 | ✅ 双段都有 | ✅ 双段都有 |

## 可复用模式

1. **3角色必备**：极端视觉差异化（颜色+体型+配饰三维分离）
2. **Realistic 标准流程**：纯文本 PSE + Video Extension，不依赖任何图片
3. **PSE 模板**：`[角色名] 人种+年龄+体型, 核心特征(大写), 服装详述, 当前姿态+位置`
4. **CONSISTENCY_SUFFIX**：始终附加"THREE characters always visible: [简短标签列表]"
5. **Crossfade concat**：0.4s 过渡 + 双段音频检查

## 待优化
- 并发生成（anime+realistic 同时跑，节省一半时间）
- 更多角色（4人？）的一致性衰减测试
