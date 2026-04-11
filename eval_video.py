#!/usr/bin/env python3
"""Evaluate V7 video using Gemini via TokenSSR."""
import sys, json, base64
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "tools"))
from config_loader import load_keys
from google import genai

keys = load_keys()
client = genai.Client(api_key=keys["gemini_key"], http_options={"base_url": keys["gemini_base_url"]})

video_path = sys.argv[1]
style_label = sys.argv[2] if len(sys.argv) > 2 else "unknown"

with open(video_path, "rb") as f:
    video_bytes = f.read()

prompt = f"""你是一个专业的短视频质量评审员。请分析这个45秒的{style_label}风格短视频（3个15秒segment拼接而成）。

故事背景：深夜创业公司办公室，程序员赵阳（28岁，黑色卫衣，蓬松黑发，黑眼圈，瘦削）深夜改bug，触发了"代码觉醒系统"，获得超能力修bug，通宵后发现还有下一关。

请评估以下维度（每个维度1-10分）：

1. **角色一致性** — 角色在3个segment之间外貌是否一致？发型、衣服颜色、脸型、体型是否变化？
2. **场景一致性** — 办公室环境是否保持一致？桌面物品、灯光、窗外景色是否连贯？
3. **衔接流畅度** — segment之间声音和画面是否有明显跳跃或断裂？
4. **中文语音质量** — 语音是否清晰？是否中文？语速是否正常？有无结巴/重复？
5. **动作速度** — 人物动作是否正常速度？有无慢动作或加速？
6. **画面质量** — 画面清晰度、色彩、构图如何？
7. **整体观感** — 作为一个45秒短视频，整体吸引力如何？

请用中文回答，每个维度给出分数和具体分析。最后给出总分（各维度加权平均）。"""

resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        genai.types.Content(parts=[
            genai.types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
            genai.types.Part.from_text(text=prompt),
        ])
    ]
)
print(resp.text)
