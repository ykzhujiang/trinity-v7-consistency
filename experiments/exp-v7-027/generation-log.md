# EXP-V7-027 Generation Log

## 实验信息
- **ID**: EXP-V7-027
- **题材**: 办公室会议 — 4人同镜头跨Segment一致性
- **角色数**: 4（BOSS, EXEC, GUY, GIRL）
- **Cycle**: 886
- **日期**: 2026-04-11T03:48+08:00

## 资产生成
- 10张参考图（4角色×2风格 + 1场景×2风格）
- Gemini concurrent, concurrency=4, 全部成功
- ⛔ 遵守 standing order: 写实版也上传了资产（原spec说text-only，被standing order覆盖）

## Seedance 参数
- **Seg1**: Image-to-video mode, 5张参考图, 15s, 9:16
- **Seg2**: Video extension mode, 从Seg1续, 15s, 9:16
- **并发策略**: anime+realistic同阶段并发, Seg1→Seg2串行

## 生成耗时
| 阶段 | anime | realistic |
|------|-------|-----------|
| Seg1 | 216s | 213s |
| Seg2 | 371s | 432s |

## 音频检查
- final-anime: ✓ 30.2s/30.1s (100%)
- final-realistic: ✓ 30.2s/30.1s (100%)

## Bug修复
- seedance_gen.py batch mode: `t["id"]` → `t.get("id", t.get("name", t["out"]))` 修复 KeyError
