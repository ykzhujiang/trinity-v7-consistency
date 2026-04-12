# V7-103 — 资产驱动 3D 动画视频（回归资产路线）

## 假设
基于资产（参考图）的视频生成比纯文生视频具有更好的角色一致性和场景稳定性。Seedance 原生音频（对白+音效+BGM）足以支撑叙事。

## 方向变化
- 从纯 text-to-video 回到 asset-based image-to-video
- 禁止外部 TTS — 所有音频由 Seedance 原生生成
- 对白写在 Seedance prompt 中，让 Seedance 自行生成语音

## 故事概念
**题材**: 程序员深夜 debug，发现 bug 是一个分号
**风格**: Genshin Impact 3D cel-shaded animation
**场景**: [INDOOR] 小型创业办公室，L型桌+显示器+台灯暖光+咖啡杯+窗外城市夜景
**角色**: 中国男性，25岁，黑色短发，灰色连帽卫衣，黑框眼镜

## 3 Segment 设计（单场景 extend chain）

### Seg1 (image-to-video, ~15s)
- 角色坐在电脑前，揉太阳穴，屏幕显示代码报错
- 对白: "第三天了...这个bug到底藏在哪..."
- 拿起咖啡杯发现空了，苦笑

### Seg2 (extend from Seg1, ~15s)
- 角色突然凑近屏幕，发现问题所在
- 对白: "等等...这行...这是个分号？三天！三天就因为一个分号！"
- 先震惊后大笑

### Seg3 (extend from Seg2, ~15s)
- 角色靠回椅子笑完，深呼吸，重新冲咖啡
- 对白: "好吧...敬每一个凌晨三点还在写代码的人"
- 端着咖啡坐回去继续敲代码，嘴角带笑

## Pipeline
1. gemini_chargen.py → 角色图 + 场景图
2. ark_asset_upload.py → 上传火山
3. seedance_gen.py --images → Seg1 (image-to-video)
4. seedance_gen.py --video seg1.mp4 → Seg2 (extend, strip audio first)
5. seedance_gen.py --video seg2.mp4 → Seg3 (extend, strip audio first)
6. ffmpeg_concat.py → 拼接最终视频

## 成功标准
- 角色一致性 ≥ 0.80
- 场景一致性 ≥ 0.85
- Seedance 原生音频有对白声音
- 物理规律正常
