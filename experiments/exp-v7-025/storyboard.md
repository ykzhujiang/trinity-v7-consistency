# EXP-V7-025: 同场景双人双Segment一致性测试

## 概要
**假设**: H-357 — 同场景+双人，能实现最高跨Segment一致性（隔离场景变量，专注人物一致性）
**题材**: 创业搭档深夜办公室对话
**风格**: 轻松幽默+温暖
**时长**: ~30秒（2×15s）

## 角色

### 角色A：李昊（男，30岁，程序员CEO）
- 175cm，黑色短发，偏瘦，小胡茬
- 穿灰色卫衣+黑色运动裤
- 画面左侧（180度法则）

### 角色B：苏晴（女，28岁，产品经理合伙人）
- 165cm，黑色马尾辫，清秀面容
- 穿白色T恤+深蓝牛仔外套+牛仔裤
- 画面右侧（180度法则）

## 场景
现代创业公司办公室，深夜。暖黄色台灯光。双屏显示器，桌上有纸杯咖啡、外卖盒残余、充电线。窗外城市夜景暖色灯光。两个工位紧挨着。

---

## Segment 1（~15秒，4 Parts）

**Physical State Anchoring**: 李昊坐在左侧工位办公椅上，双手搭在键盘边缘，身体靠向椅背。苏晴坐在右侧工位，面朝自己的显示器。桌上两杯咖啡（李昊的空了）。

[Part 1] Medium two-shot from front, A on left B on right. A stares at monitor showing red error code, lets out long sigh, pushes himself back in chair with both hands on desk edge. Chair rolls backward slightly. B glances sideways at A without turning head. A says "完了…这个支付接口又崩了…第四次了…"

[Part 2] Medium close-up on B from slightly right. B picks up her coffee cup with right hand, takes a sip, then reaches with left hand to grab a second full coffee cup from her desk. She turns chair to face A, extends the cup toward him. She says "别急，先喝口咖啡，我看看。"

[Part 3] Over-the-shoulder from behind A, facing B. B rolls her chair to A's desk, leans forward to look at A's screen. Her left hand points at a specific line of code on screen. Her eyes narrow, studying. A holds the coffee with both hands, watching her. No dialogue. Keyboard click sounds as B scrolls with A's mouse.

[Part 4] Medium two-shot. B taps the Enter key once. Screen flashes from red error to green success. A's jaw drops, eyes widen. B leans back in chair, crosses arms with a satisfied smirk. A stares at screen then at B, mouth still open. A says "…就…就这样？一行就修好了？" ~1 second silence at end.

---

## Segment 2（~15秒，4 Parts）

**Physical State Anchoring**: 同一间办公室，同一暖黄灯光。李昊坐在左侧工位椅上，手握咖啡杯。苏晴坐在李昊工位旁（上一Segment结尾她滚椅过来了），双臂交叉靠在椅背上。显示器显示绿色成功。

[Part 1] Medium shot from front. A puts coffee cup down on desk with right hand, stands up, stretches both arms high above head with fingers interlocked. He twists torso left then right. He says "你怎么每次都能一下找到问题…我debug四个小时白折腾了…"

[Part 2] Close-up on B, warm light on face. B tilts head slightly, smiles showing teeth, index finger of right hand points at A's screen. She says "因为这个bug上次你也写过一模一样的。" B's eyebrows rise teasingly.

[Part 3] Medium two-shot from slightly left. A freezes mid-stretch, slowly lowers arms. His face turns slightly red, mouth forms an exaggerated 'O'. He covers face with both palms. He says "不是吧…一模一样的？我以为我修过了…"

[Part 4] Medium-wide two-shot, warm backlight from desk lamp. B reaches out with right hand and pats A's left shoulder twice. Both burst into laughter. A drops hands from face, shaking head. B's head tilts back as she laughs. No dialogue. Office ambient hum + their laughter. ~1 second silence at end.

---

## 技术约束
- ⛔ 同场景同机位基准：办公室布局/灯光/物品完全一致
- ⛔ A始终画面左，B始终画面右（180度法则）
- ⛔ 角色外貌服装两Segment完全一致
- ⛔ 禁止慢动作、禁止面对镜头
- ⛔ 台词密度≥80%
- ⛔ 所有台词14秒前说完，预留1秒静默缓冲
