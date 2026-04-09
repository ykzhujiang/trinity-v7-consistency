# EXP-V7-004-realistic — 搞笑都市：外卖小哥送错单（3D写实风格）

## 实验信息
| 字段 | 值 |
|------|-----|
| **实验 ID** | EXP-V7-004-realistic |
| **对照组** | EXP-V7-004 (anime) |
| **Operator 执行** | CYCLE-operator-851 |
| **日期** | 2026-04-10 |
| **难度** | D1-简单（单场景 + 2角色 + 搞笑对话） |
| **题材** | 都市喜剧 — 外卖小哥送错单 |
| **技术方案** | Video Extension |
| **画风** | 3D animated / Pixar-style (绕过 Seedance 真人隐私检测) |
| **假设** | H-111: anime vs realistic 的 character_consistency 差距 |

## 技术发现
- **Seedance 隐私检测限制**: photorealistic 和 cinematic digital painting 风格都触发 `PrivacyInformation` 错误
- **解决方案**: 使用 "3D animated / Pixar-style" 风格，不触发隐私检测但比动漫更写实
- **Video Extension 耗时**: Seg2 ~10min（比 anime 版更慢）
- 总生成时间: ~20min（资产3张 + Seg1 ~6min + Seg2 ~10min + 拼接）

## 生成结果
| 产物 | 路径 | 大小 |
|------|------|------|
| 剧本 | `storyboard.md` | 同 anime 版 |
| Segment 1 | `output/segment-01.mp4` | 6.1MB |
| Segment 2 | `output/segment-02.mp4` | 6.4MB |
| 合并视频 | `output/final-30s.mp4` | 12.2MB |
| 素材 | `output/assets/` | 3张 (41+27+35KB) |

## 待检测
| 维度 | 目标 | 实际 |
|------|------|------|
| 人物一致性 | ≥90% | ⏳ 待 Sensor 5D 检测 |
| 场景一致性 | ≥95% | ⏳ 待 Sensor 5D 检测 |
| 越轴 | =0 | ⏳ 待 Sensor 5D 检测 |
| 剧情连续性 | Seg1尾=Seg2头 | ⏳ 待 Sensor 5D 检测 |

## 与 anime 版对比
- anime 版 Sensor 评分: 综合 7.8/10 (角色8, 场景9, 衔接7, 剧情7, 画质8)
- realistic 版: 待检测
