# EXP-V7-004 — 搞笑都市：外卖小哥送错单

## 实验信息
| 字段 | 值 |
|------|-----|
| **实验 ID** | EXP-V7-004 |
| **Controller 设计** | CYCLE-controller-1273 (V7 实验扩展计划) |
| **Operator 执行** | CYCLE-operator-850 |
| **日期** | 2026-04-10 |
| **难度** | D1-简单（单场景 + 2角色 + 搞笑对话） |
| **题材** | 都市喜剧 — 外卖小哥送错单 |
| **技术方案** | Video Extension |
| **假设** | H-106: 搞笑场景中大幅度表情变化不影响人物一致性（≥90%） |

## 执行参数
- 剧本: S-Format, 2 Segments × 4 Parts
- 画风: 动漫插画（Seedance 隐私检测限制）
- 比例: 9:16 竖屏
- 素材: Gemini 生成（小刘 66KB, 林姐 39KB, 场景 44KB）
- Seg1: Seedance 2.0 + 3张参考图
- Seg2: Video Extension（@video1 续写）

## 生成结果
| 产物 | 路径 | 大小 |
|------|------|------|
| 剧本 | `storyboard.md` | - |
| Segment 1 | `output/segment-01.mp4` | 7.2MB |
| Segment 2 | `output/segment-02.mp4` | 8.2MB |
| 合并视频 | `output/final-30s.mp4` | ~15MB |
| 素材 | `output/assets/` | - |

## 成功标准 vs 实际
| 维度 | 目标 | 实际 |
|------|------|------|
| 人物一致性 | ≥90% | ⏳ 待检测 |
| 场景一致性 | ≥95% | ⏳ 待检测 |
| 越轴 | =0 | ⏳ 待检测 |
| 剧情连续性 | Seg1尾=Seg2头 | ⏳ 待检测 |

## 技术发现
- Pipeline 修复: 本地视频自动上传 tmpfiles.org 后传给 Seedance
- Seedance 生成时间: Seg1 ~3min, Seg2 ~8min (Video Extension 更慢)
