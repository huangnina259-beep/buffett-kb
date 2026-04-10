import type { Module, Message, CurriculumState } from '../types'

export const CURRICULUM: Module[] = [
  {
    id: 1,
    title: '读懂这门生意',
    description: '可口可乐靠什么赚钱',
    cycles: [
      {
        id: '1.1',
        title: '商业模式',
        hint: '去找可口可乐最近一份年报（10-K）的 Business Overview，第一到第三页。找 "concentrate"（浓缩液）这个词——看它卖给谁，谁负责生产最终产品。',
      },
      {
        id: '1.2',
        title: '轻资产验证',
        hint: '年报现金流量表里找 Capital Expenditures（资本支出），在 Investing Activities 那一栏。除以当年营收算百分比，做十年，再和百事可乐的同一数字对比。',
      },
      {
        id: '1.3',
        title: '模式总结',
        hint: '回顾你在 1.1 和 1.2 得出的结论，用三句话概括：(1) 靠什么赚钱 (2) 为什么资本轻 (3) 什么最难被复制。',
      },
    ],
    frameworkItems: [
      '区分"产品"和"商业模式"',
      '用资本支出/营收比验证轻资产',
      '一句话说清商业模式',
    ],
  },
  {
    id: 2,
    title: '护城河',
    description: '为什么竞争对手打不进来',
    cycles: [
      {
        id: '2.1',
        title: '定价权测试',
        hint: '找过去 15 年的毛利率数据，重点看 2008 金融危机和 2020 疫情期间的变化幅度，和百事对比。',
      },
      {
        id: '2.2',
        title: '品牌 vs 分销',
        hint: '思考：如果可口可乐的品牌消失了，只剩产品本身，消费者还会买吗？这个答案告诉你品牌到底值多少。',
      },
      {
        id: '2.3',
        title: '护城河方向',
        hint: '看过去十年的市场份额变化、新品类渗透率、年轻消费者偏好调研，判断护城河在变宽还是变窄。',
      },
    ],
    frameworkItems: [
      '压力期毛利率稳定性 = 定价权指纹',
      '品牌消失测试',
      '护城河方向判断',
    ],
  },
  {
    id: 3,
    title: '财务质量',
    description: '数字上能印证护城河吗',
    cycles: [
      {
        id: '3.1',
        title: 'ROIC 计算',
        hint: '用 NOPAT / Invested Capital 计算 ROIC，和百事、雀巢对比。注意排除商誉和无形资产的影响。',
      },
      {
        id: '3.2',
        title: '复投能力',
        hint: '高 ROIC 不够，还要看有没有地方把钱投回去。看可口可乐的营收增长来源：新市场、新品类、提价？',
      },
    ],
    frameworkItems: [
      'ROIC 计算与同行对比',
      '高 ROIC + 复投机会 = 复利机器',
    ],
  },
  {
    id: 4,
    title: '管理层',
    description: '这些人值得信任吗',
    cycles: [
      {
        id: '4.1',
        title: '资本配置历史',
        hint: '查过去五年的现金流分配：分红、回购、并购、再投资各占多少？每项的回报率如何？',
      },
      {
        id: '4.2',
        title: '股东导向',
        hint: '看回购时机——是在股价便宜时买还是不管价格都在买？对比 EPS 增长和真实业务增长。',
      },
    ],
    frameworkItems: [
      '追踪现金去向',
      '回购时机合理性判断',
    ],
  },
  {
    id: 5,
    title: '估值与决策',
    description: '好公司，现在买合适吗',
    cycles: [
      {
        id: '5.1',
        title: '好公司 vs 好投资',
        hint: '算一下：如果用当前 PE 买入，假设未来 10 年 EPS 增长 5%/年，你的年化回报是多少？',
      },
      {
        id: '5.2',
        title: '逆向思维',
        hint: '列出所有可能让这笔投资亏损 50% 的情景。每个情景的概率有多大？这是芒格的 inversion。',
      },
      {
        id: '5.3',
        title: '能力圈',
        hint: '诚实回答：你对这门生意的理解，有哪些是真正确定的，哪些其实只是假设？',
      },
    ],
    frameworkItems: [
      '隐含增长率倒推',
      '逆向清单（inversion checklist）',
      '能力圈边界自检',
    ],
  },
]

/* ── Opening messages ─────────────────────────────────────────── */

export const OPENING_MESSAGES: Message[] = [
  {
    id: 'intro',
    role: 'tutor',
    content:
      '我读过巴菲特写给股东的每一封信，从1977年到今天。芒格的每一场演讲。Howard Marks的每一份备忘录。李录的著作。\n\n我不是一个人。但他们说过的话，我没有忘记一个字。',
    timestamp: Date.now(),
  },
  {
    id: 'method',
    role: 'tutor',
    content:
      '大多数课程会给你一套框架然后解释它。我不打算那样做——因为那样做没用。真正的分析能力只能通过一件事学会：做。\n\n我会给你问题，告诉你去哪里找答案。你来找，你来答。答对了我们继续，答错了我们想清楚为什么，然后继续。\n\n学完之后你手里会有一套自己填出来的分析框架——以后分析任何一家公司都能用。',
    timestamp: Date.now() + 1,
  },
  {
    id: 'q1',
    role: 'tutor',
    content:
      '我们从最基础的地方开始。今天的案例是可口可乐。\n\n**可口可乐是一家什么公司？用一句话告诉我：它靠什么赚钱，钱从谁那里来。**\n\n不要说"卖饮料"——我要的是钱的流向。',
    timestamp: Date.now() + 2,
  },
]

/* ── Initial state ────────────────────────────────────────────── */

export const INITIAL_STATE: CurriculumState = {
  currentModule: 1,
  currentCycle: '1.1',
  completedCycles: [],
  frameworkInsights: [],
  parkingLot: [],
}
