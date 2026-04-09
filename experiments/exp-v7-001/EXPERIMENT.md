# EXP-V7-001 — Video Extension 连续性基线测试

## 实验信息
| 字段 | 值 |
|------|-----|
| **实验 ID** | EXP-V7-001 |
| **Controller 设计** | CYCLE-controller-1272 (V7 战略升级) |
| **Operator 执行** | CYCLE-operator-849 |
| **日期** | 2026-04-10 |
| **难度** | D1-简单（单场景 + 2角色 + 对话） |
| **题材** | 都市现代 — 办公室对话 |
| **技术方案** | Video Extension（Seg2 = Extend @video1） |

## 假设
Video Extension 模式下，Seedance 2.0 能保持跨 Segment 的人物和场景一致性（≥90%）。

## 执行参数
- **剧本格式**: S-Format v7.5, 2 Segments × 4 Parts
- **画风**: 动漫/插画风格（写实风被 Seedance 隐私检测拒绝）
- **比例**: 9:16 竖屏
- **素材生成**: Gemini（角色肖像 + 场景图）
- **视频生成**: Seedance 2.0 via EvoLink API

## 技术发现
1. **Seedance 隐私检测**: 写实人物肖像被拒，必须用动漫/插画风格
2. **视频上传**: Seedance 不接受本地视频，需公网 URL。catbox 不可用，tmpfiles.org 可用
3. **Video Extension 模式**: 只传入 @video1 和 prompt，不传额外参考图

## 生成结果
| 产物 | 路径 |
|------|------|
| 剧本 | `experiments/exp-v7-001/storyboard.md` |
| Segment 1 | `experiments/exp-v7-001/output/segment-01.mp4` |
| Segment 2 | `experiments/exp-v7-001/output/segment-02.mp4` |
| 合并视频 | `experiments/exp-v7-001/output/final-30s.mp4` |
| 素材 | `experiments/exp-v7-001/output/assets/` |

## 一致性评分
⏳ 待 Sensor 多维度检测

## 备注
- 首次成功生成 30 秒双 Segment 视频
- 基线建立，后续实验将在此基础上对比
