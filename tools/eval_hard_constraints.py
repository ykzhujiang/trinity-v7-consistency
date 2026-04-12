#!/usr/bin/env python3
"""
V7 Video Hard Constraint Evaluator
===================================
Evaluates videos on 3 hard constraints using Gemini 3.1 via TokenSSR:
  1. Consistency — character/costume/scene element stability across segments
  2. Continuity  — action/plot/timeline coherence across segments
  3. Physics     — physical plausibility (gravity, collision, occlusion, no clipping)

Usage:
  python eval_hard_constraints.py <video_path> [--storyboard <md_path>] [--style <label>] [--segments <N>]

Output: JSON to stdout with per-dimension scores (0-10), issues, and weighted total.
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config_loader import load_keys

try:
    from google import genai
except ImportError:
    sys.exit("ERROR: google-genai not installed. Run: pip install google-genai")


def build_prompt(style: str, segments: int, storyboard_text: str | None) -> str:
    sb_section = ""
    if storyboard_text:
        sb_section = f"""
## 参考剧本（Storyboard）
以下是该视频的剧本，用于对照检查内容是否与剧本一致：
<storyboard>
{storyboard_text[:4000]}
</storyboard>
"""

    return f"""你是一个专业的AI生成视频质量评审系统。请严格按照以下3个硬约束维度评估这个{segments*15}秒的{style}风格短视频（{segments}个15秒segment拼接）。

{sb_section}

## 评估维度

### 1. 一致性 (Consistency) — 权重 40%
评估角色和场景元素在跨Segment之间是否保持一致：
- 角色外貌：脸型、发型、发色、肤色是否在不同segment中保持稳定
- 角色服装：衣服款式、颜色、配饰是否一致
- 角色体型：身高、体型比例是否一致
- 场景元素：家具、灯光、背景物品是否保持稳定
- 色调/画风：整体色调和风格是否统一

### 2. 连续性 (Continuity) — 权重 35%
评估动作、情节和时间线在跨Segment之间是否连贯衔接：
- 动作连续：segment切换处的动作是否自然衔接（无跳跃/重置）
- 姿态连续：角色在切换点的姿势是否与前一段结束时一致
- 情节连续：故事线是否逻辑连贯（不出现剧情跳跃或重复）
- 音频连续：声音（对白/音乐/音效）在切换点是否自然过渡（无断裂/重复/音量跳变）
- 时间连续：时间流是否自然（无突然变速/倒退）

### 3. 物理规律 (Physics) — 权重 25%
评估物理行为是否符合常识：
- 重力：物体是否正常受重力影响（无悬浮/反重力）
- 碰撞/穿模：物体和角色是否有穿透现象（手穿过桌子等）
- 遮挡关系：前后遮挡是否正确（近物遮远物）
- 光影：光源方向和阴影是否一致
- 物体行为：液体、布料、头发等是否有合理的物理表现

## 输出要求

请严格按照以下JSON格式输出（不要加markdown代码块标记），不要添加任何额外文字：

{{
  "consistency": {{
    "score": <0-10的整数>,
    "issues": ["具体问题1", "具体问题2"],
    "details": "详细分析文字"
  }},
  "continuity": {{
    "score": <0-10的整数>,
    "issues": ["具体问题1", "具体问题2"],
    "details": "详细分析文字"
  }},
  "physics": {{
    "score": <0-10的整数>,
    "issues": ["具体问题1", "具体问题2"],
    "details": "详细分析文字"
  }},
  "total_score": <加权平均，保留1位小数>,
  "summary": "一句话总结",
  "pass": <true如果total_score>=7.0，否则false>
}}

评分标准：
- 10: 完美，无可察觉问题
- 8-9: 优秀，极少细微问题
- 6-7: 合格，有明显但不致命的问题
- 4-5: 不合格，有严重问题影响观看
- 1-3: 极差，问题严重到无法正常观看
- 0: 完全无法评估

请仔细逐帧分析，特别关注segment切换点（约第15秒和第30秒处）。"""


def evaluate(video_path: str, style: str = "unknown", segments: int = 3,
             storyboard_path: str | None = None) -> dict:
    keys = load_keys()
    if not keys.get("gemini_key"):
        return {"error": "No Gemini API key found"}

    client = genai.Client(
        api_key=keys["gemini_key"],
        http_options={"base_url": keys["gemini_base_url"]} if keys.get("gemini_base_url") else {}
    )

    with open(video_path, "rb") as f:
        video_bytes = f.read()

    storyboard_text = None
    if storyboard_path and Path(storyboard_path).exists():
        storyboard_text = Path(storyboard_path).read_text(encoding="utf-8")

    prompt = build_prompt(style, segments, storyboard_text)

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            genai.types.Content(parts=[
                genai.types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
                genai.types.Part.from_text(text=prompt),
            ])
        ]
    )

    raw = resp.text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: try to extract JSON from response
        import re
        m = re.search(r'\{.*\}', raw, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group())
            except json.JSONDecodeError:
                result = {"error": "Failed to parse Gemini response", "raw": raw}
        else:
            result = {"error": "No JSON found in response", "raw": raw}

    # Recompute weighted total for consistency
    if "error" not in result and all(k in result for k in ("consistency", "continuity", "physics")):
        c = result["consistency"]["score"]
        t = result["continuity"]["score"]
        p = result["physics"]["score"]
        result["total_score"] = round(c * 0.4 + t * 0.35 + p * 0.25, 1)
        result["pass"] = result["total_score"] >= 7.0

    result["meta"] = {
        "video": video_path,
        "style": style,
        "segments": segments,
        "storyboard": storyboard_path,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="V7 Video Hard Constraint Evaluator")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("--storyboard", help="Path to storyboard markdown (optional)")
    parser.add_argument("--style", default="unknown", help="Visual style label (e.g. genshin, pixar)")
    parser.add_argument("--segments", type=int, default=3, help="Number of 15s segments (default: 3)")
    args = parser.parse_args()

    if not Path(args.video).exists():
        print(json.dumps({"error": f"Video not found: {args.video}"}))
        sys.exit(1)

    result = evaluate(args.video, args.style, args.segments, args.storyboard)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
