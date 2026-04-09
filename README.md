# Trinity V7 — Dual Segment Consistency Research

双 Segment (~30秒) 短剧一致性研究项目。

## 目标
攻关跨 Segment 一致性：人物、场景、机位、剧情连续性。

## 实验计划
- **EXP-V7-001**: Video Extension 连续性基线测试
- **EXP-V7-002**: First Frame Anchoring 对比测试
- **EXP-V7-003**: Hybrid 方案测试

## 技术栈
- Seedance 2.0 API (via EvoLink)
- Gemini (角色/场景素材生成)
- Python pipeline scripts

## 4 个刚性约束
1. 人物一致性 — 面孔/体型/服装
2. 场景一致性 — 不同机位下同一场景
3. 机位连续性 & 越轴 — 180度规则
4. 剧情连续性 — 动作/状态衔接
