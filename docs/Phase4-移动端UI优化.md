# Phase 4：移动端 UI 优化汇总

> 日期：2026-09-19

## 一、已完成优化

1. **防止横向滚动**：`html, body { overflow-x: hidden }`，`box-sizing: border-box`
2. **学号/姓名不换行**：`white-space: nowrap`，等宽字体显示学号
3. **小屏适配（≤400px）**：
   - 学生姓名从 18px 缩到 16px
   - 状态按钮字号 14px→13px，最小高度 44px→42px
   - 顶部统计字号 13px→12px，padding 收紧
   - 筛选 chip 字号 13px→12px
4. **底部安全区**：`padding-bottom: env(safe-area-inset-bottom)`，适配 iPhone 刘海屏
5. **body padding**：`.body-pad` 从 90px 增到 110px，防止内容被固定底栏遮挡
6. **状态按钮 grid**：4 列等宽，gap 6px，小屏下仍可点击
7. **顶部统计 chips**：flex-wrap 自动换行，不会溢出

## 二、实测验证

| 项目 | 结果 |
|---|---|
| scrollWidth === clientWidth | 无横向滚动 |
| 学生卡片 | 学号、姓名、电话、4 按钮全部一屏可见 |
| 状态选中 | 绿/橙/蓝/紫明显区分 |
| 搜索 | 输入即时过滤，无弹窗 |
| 筛选 chips | 点击切换，只显示对应状态学生 |
| 历史列表 | 日期倒序，时间+统计完整 |
| 历史详情 | 每个学生状态着色，导出按钮可见 |
| 底部按钮 | 历史/花名册/导出/结束 全部可点击 |

## 三、下一阶段（Phase 5）需要做什么

- 5 个班各导入 50 名学生
- 同一天多次点名（创建多个 session）
- 测试页面刷新后恢复未完成点名
- 测试 Excel 重复导入（旧名单替换）
- 测试批量导出（多 session 合并）
- 检查完成验收清单
