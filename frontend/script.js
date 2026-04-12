let chatHistory = [];
let lastSources = [];
let isGenerating = false;
let hasStartedChat = false;
let currentLang = localStorage.getItem('lang') || 'zh';
let userScrolledUp = false;

// ─── Language Strings ──────────────────────────────────────────
const LANG = {
    zh: {
        headline: '向大师学习，独立思考。',
        subheadline: '探索巴菲特、芒格、霍华德·马克斯和李录的投资智慧。',
        cardQaTitle: '提问投资问题',
        cardQaDesc: '探索巴菲特、芒格、马克斯和李录的思想。',
        cardQaCta: '进入问答 →',
        cardTrainTitle: '实践课程',
        cardTrainDesc: '跟着学习地图，用可口可乐真实案例把投资框架学明白。',
        cardTrainCta: '开始实践 →',
        footerLine: '商业 · 思维 · 风险 · 时间',
        preChatTitle: '向大师学习。',
        preChatPlaceholder: '询问任何价值投资相关问题…',
        chatPlaceholder: '继续提问…',
        loadingText: '正在分析知识库…',
        newChat: '+ 新对话',
        brandText: '价值投资',
        sidebarSourceTitle: '来源片段',
        trainingBack: '← 主页',
        insightLabel: '巴菲特的视角',
        continueBtn: '继续 →',
        summaryBtn: '查看总结 →',
        summaryComplete: '完成',
        summaryCaseLabel: '案例研究',
        summarySubtitle: '分歧不是失败——这正是真正思考的起点。',
        summaryActionBack: '← 返回主页',
        summaryActionChat: '向知识库提问 →',
        summaryScoreText: (m, t) => `你与巴菲特的思维框架在 ${m}/${t} 个步骤上一致。`,
        caseSelectorLabel: '案例研究',
        caseSelectorSub: '每个案例通过巴菲特的框架探索一项真实投资。',
        stepOf: (c, t) => `第 ${c} / ${t} 步`,
        yourAnswer: '你的答案',
        buffettFramework: '巴菲特的框架',
        suggestions: [
            '巴菲特如何判断一家公司是否值得长期持有？',
            '什么是护城河？如何识别一家公司的护城河？',
            '芒格的投资检查清单包含哪些核心要素？',
            '价值投资者如何看待市场波动和短期下跌？'
        ],
    },
    en: {
        headline: 'Learn from the masters. Think for yourself.',
        subheadline: 'Explore the investment wisdom of Buffett, Munger, Marks, and Li Lu.',
        cardQaTitle: 'Ask Investment Questions',
        cardQaDesc: 'Explore ideas from Buffett, Munger, Marks, and Li Lu.',
        cardQaCta: 'Enter Q&A →',
        cardTrainTitle: 'Practice Course',
        cardTrainDesc: 'Follow the learning map and master the investment framework with a real Coca-Cola case.',
        cardTrainCta: 'Start Course →',
        footerLine: 'Business · Thinking · Risk · Time',
        preChatTitle: 'Learn from the masters.',
        preChatPlaceholder: 'Ask anything about value investing...',
        chatPlaceholder: 'Ask a follow-up question...',
        loadingText: 'Analyzing wisdom sources...',
        newChat: '+ New Chat',
        brandText: 'Value Investing',
        sidebarSourceTitle: 'Source Fragment',
        trainingBack: '← Home',
        insightLabel: "Buffett's Perspective",
        continueBtn: 'Continue →',
        summaryBtn: 'See Summary →',
        summaryComplete: 'Complete',
        summaryCaseLabel: 'Case Study',
        summarySubtitle: "Divergence isn't failure — it's where the real thinking starts.",
        summaryActionBack: '← Back to Home',
        summaryActionChat: 'Ask the Knowledge Base →',
        summaryScoreText: (m, t) => `You aligned with Buffett's framework on ${m} of ${t} steps.`,
        caseSelectorLabel: 'Case Studies',
        caseSelectorSub: "Each case explores one real investment through Buffett's framework.",
        stepOf: (c, t) => `Step ${c} of ${t}`,
        yourAnswer: 'Your answer',
        buffettFramework: "Buffett's framework",
        suggestions: [
            'How does Buffett evaluate whether a company is worth holding long-term?',
            "What is a moat? How do you identify a company's competitive advantage?",
            "What are the core elements of Munger's investment checklist?",
            'How do value investors view market volatility and short-term declines?'
        ],
    }
};

// ─── Training Cases (bilingual) ─────────────────────────────────
const TRAINING_CASES = {
    'coca-cola': {
        title:    { en: 'Coca-Cola, 1988',              zh: '可口可乐，1988年' },
        year:     '1988',
        subtitle: { en: 'How Buffett Made His Biggest Bet', zh: '巴菲特如何押下他最大的赌注' },
        steps: [
            {
                theme: { en: 'Business Model', zh: '商业模式' },
                context: {
                    en: "It's 1988. Warren Buffett is reading Coca-Cola's annual report. The company earns most of its revenue by selling syrup concentrate to independent bottlers worldwide. Those bottlers handle all the capital-intensive manufacturing, canning, and distribution.",
                    zh: "1988年，沃伦·巴菲特正在阅读可口可乐的年报。公司大部分收入来自向全球独立装瓶商出售糖浆浓缩液。装瓶商负责所有资本密集型的生产、灌装和分销工作。"
                },
                question: {
                    en: "What makes Coca-Cola's core business model economically powerful?",
                    zh: "是什么让可口可乐的核心商业模式具有强大的经济竞争力？"
                },
                options: {
                    en: [
                        "It owns and operates every bottling plant worldwide, giving it total supply-chain control.",
                        "It sells high-margin syrup concentrate to bottlers, keeping the business asset-light with exceptional returns on invested capital.",
                        "Its advantage comes from access to cheap sugar and water inputs that competitors can't match.",
                        "It runs a diversified conglomerate spanning beverages, food, and entertainment."
                    ],
                    zh: [
                        "它在全球拥有并运营每一家装瓶厂，从而实现对供应链的完全控制。",
                        "它向装瓶商出售高利润率的糖浆浓缩液，保持轻资产运营，投资资本回报率极为出色。",
                        "其优势来自于竞争对手无法匹敌的廉价糖和水的供应渠道。",
                        "它是一家跨越饮料、食品和娱乐领域的多元化企业集团。"
                    ]
                },
                correct: 1,
                insight: {
                    en: "Coca-Cola's genius is structural: it sells concentrate at high margins while independent bottlers absorb the capital-intensive manufacturing. This asset-light model earns extraordinary returns on invested capital. Buffett estimated Coke earned roughly $1 on every $2 of tangible assets deployed — a return profile most businesses can't approach.",
                    zh: "可口可乐的商业天才在于其结构设计：以高利润率出售浓缩液，而资本密集型生产则由独立装瓶商承担。这种轻资产模式创造了极高的投资资本回报率。巴菲特估计，可口可乐每投入2美元有形资产，大约能赚取1美元——这是大多数企业难以企及的盈利能力。"
                },
                attribution: {
                    en: 'Buffett has praised this model repeatedly in shareholder letters, noting the "fountainhead of value" created by brand plus asset-light structure.',
                    zh: '巴菲特多次在致股东信中称赞这一模式，指出品牌加轻资产结构创造的"价值之源"。'
                }
            },
            {
                theme: { en: 'Competitive Moat', zh: '竞争护城河' },
                context: {
                    en: "In blind taste tests — including the famous Pepsi Challenge — Pepsi consistently outperforms Coke in head-to-head sips. Yet Coca-Cola outsells Pepsi globally by a wide margin, across more than 200 countries.",
                    zh: '在盲测中——包括著名的"百事挑战"——百事可乐在直接对比品尝中始终胜出。然而，可口可乐在全球超过200个国家的销量远超百事可乐。'
                },
                question: {
                    en: "What type of competitive moat does the Pepsi Challenge paradox reveal?",
                    zh: '"百事挑战"悖论揭示了哪种类型的竞争护城河？'
                },
                options: {
                    en: [
                        "Cost moat — Coke produces its product cheaper than any competitor.",
                        "Network effects — more Coke drinkers make the product more valuable for each drinker.",
                        "Intangible brand moat — emotional habit, identity, and memory that persists despite taste preference.",
                        "Switching cost moat — consumers face significant friction when trying to switch beverages."
                    ],
                    zh: [
                        "成本护城河——可口可乐比任何竞争对手生产成本更低。",
                        "网络效应——可乐饮用者越多，产品对每位饮用者的价值就越高。",
                        "无形品牌护城河——超越口味偏好而持续存在的情感习惯、身份认同和记忆。",
                        "转换成本护城河——消费者在转换饮料时面临巨大阻力。"
                    ]
                },
                correct: 2,
                insight: {
                    en: "The Pepsi Challenge paradox is the clearest illustration of brand moat. People buy Coke for reasons entirely disconnected from the liquid — ritual, identity, global ubiquity, memory. Buffett called this \"share of mind.\" A brand embedded in the habits of billions compounds its moat with every generation. The cost to replicate it: incalculable.",
                    zh: '"百事挑战"悖论是品牌护城河最清晰的例证。人们购买可口可乐的理由与饮料本身完全无关——它关乎仪式感、身份认同和记忆。巴菲特将这称为"心智占有率"。一个深植于数十亿人习惯中的品牌，每一代人都在强化其护城河，复制它的成本无法估量。'
                },
                attribution: {
                    en: 'Buffett, 1993 Letter: "Coca-Cola... has the most powerful brand in the world."',
                    zh: '巴菲特，1993年致股东信："可口可乐……拥有世界上最强大的品牌。"'
                }
            },
            {
                theme: { en: 'Management & Capital Allocation', zh: '管理层与资本配置' },
                context: {
                    en: "Roberto Goizueta became Coca-Cola's CEO in 1981. He sold the film studio Columbia Pictures, refocused the company entirely on beverages, expanded into new global markets, and aggressively repurchased Coca-Cola shares throughout the decade.",
                    zh: "罗伯托·戈伊苏埃塔于1981年出任可口可乐CEO。他出售了哥伦比亚电影公司，将公司重新聚焦于饮料业务，拓展全球新市场，并在整个十年间积极回购可口可乐股票。"
                },
                question: {
                    en: "What does Goizueta's capital allocation track record reveal?",
                    zh: "戈伊苏埃塔的资本配置记录揭示了什么？"
                },
                options: {
                    en: [
                        "Selling assets and buying back stock signals a company that has run out of growth ideas.",
                        "Diversifying into film showed bold, forward-thinking strategic leadership.",
                        "He identified that Coke's highest-return use of capital was buying back its own undervalued stock rather than diversifying into unrelated businesses.",
                        "Share repurchases primarily benefit executives holding stock options, not ordinary shareholders."
                    ],
                    zh: [
                        "出售资产和回购股票表明一家已经没有增长方向的公司。",
                        "进军电影业体现了大胆前瞻的战略领导力。",
                        "他认识到可口可乐资本的最高回报用途，是回购自身被低估的股票，而非多元化进入无关业务。",
                        "股票回购主要使持有股票期权的高管受益，而非普通股东。"
                    ]
                },
                correct: 2,
                insight: {
                    en: "Buffett considers capital allocation the single most important skill of a CEO. Goizueta's discipline — divest unrelated businesses, reinvest in the core franchise, return capital via buybacks when the stock is cheap — is the playbook. The result: Coke's intrinsic value grew roughly 7× between 1981 and 1988. Buffett specifically cited Goizueta's management as central to his investment conviction.",
                    zh: "巴菲特认为资本配置是CEO最重要的单一技能。戈伊苏埃塔的纪律性——剥离非核心业务、将资本再投入核心特许经营权、在股价低估时通过回购返还资本——就是这一思路的完美体现。结果：1981年至1988年间，可乐的内在价值增长了约7倍。"
                },
                attribution: {
                    en: 'Buffett, 1989 Letter: "Roberto Goizueta... has led Coca-Cola with extraordinary skill."',
                    zh: '巴菲特，1989年致股东信："罗伯托·戈伊苏埃塔……以非凡的才能领导可口可乐。"'
                }
            },
            {
                theme: { en: 'Valuation & Margin of Safety', zh: '估值与安全边际' },
                context: {
                    en: "Buffett paid roughly 15× earnings for Coca-Cola in 1988. The S&P 500 averaged about 11× earnings at the time. Several Wall Street analysts questioned whether this was truly a value investment given the premium to the market.",
                    zh: "1988年，巴菲特以约15倍市盈率买入可口可乐。当时标普500的平均市盈率约为11倍。几位华尔街分析师质疑这是否真的是价值投资，因为其估值溢价于市场整体水平。"
                },
                question: {
                    en: "For a business with Coke's durability and growth profile, where is the real margin of safety?",
                    zh: "对于可口可乐这样具有持久性和增长潜力的企业，真正的安全边际在哪里？"
                },
                options: {
                    en: [
                        "There is none — paying 15× was a violation of Graham's core principles.",
                        "Safety comes from the hard asset value on the balance sheet — buildings, equipment, inventory.",
                        "For a predictable, durable compounder, the safety lives in earnings power over a 10–20 year horizon, not the entry price alone.",
                        "Safety comes from Coke's commodity hedges on sugar and aluminum prices."
                    ],
                    zh: [
                        "根本没有——支付15倍市盈率违反了格雷厄姆的核心原则。",
                        "安全性来自资产负债表上的硬资产价值——建筑物、设备、库存。",
                        "对于盈利可预期、持续性强的复利型企业，安全边际体现在未来10-20年的盈利能力上，而不仅仅是买入价格。",
                        "安全性来自可口可乐对糖和铝原材料价格的对冲。"
                    ]
                },
                correct: 2,
                insight: {
                    en: "This is where Buffett diverged from Graham's strict asset-based framework, heavily influenced by Munger. A business growing earnings reliably at 15% per year, bought at 15×, compounds dramatically over decades. Buffett later crystallized it: \"It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price.\" Price is what you pay once. Earnings power works for you every year.",
                    zh: '这正是巴菲特在芒格的影响下，开始偏离格雷厄姆严格资产基础框架的地方。一家盈利每年可靠增长15%的企业，以15倍市盈率买入，数十年后将呈现惊人的复利效果。巴菲特后来将其精炼为："以合理价格买入优秀企业，远胜于以优惠价格买入平庸企业。"价格只支付一次，盈利能力却年年为你工作。'
                },
                attribution: {
                    en: 'Buffett, 1992 Letter — describing the shift from cigar-butt investing to quality compounders.',
                    zh: '巴菲特，1992年致股东信——描述从"烟蒂投资"向优质复利型企业的转变。'
                }
            },
            {
                theme: { en: 'The Hold Decision', zh: '持有决策' },
                context: {
                    en: "By 1998, Buffett's $1 billion Coca-Cola position had grown to over $13 billion — a 13× return in 10 years. The stock now traded at approximately 50× earnings, far above any conventional valuation threshold. By every standard metric, it appeared significantly overvalued.",
                    zh: "到1998年，巴菲特10亿美元的可口可乐持仓已增值至逾130亿美元——10年内13倍的回报。股价此时约以50倍市盈率交易，远超任何传统估值基准。按每一项常规指标来看，它都显著高估。"
                },
                question: {
                    en: "What is the rational case for NOT selling at 50× earnings?",
                    zh: "在50倍市盈率时不卖出的理性依据是什么？"
                },
                options: {
                    en: [
                        "Buffett was anchored to his cost basis — a well-known psychological bias that prevents rational selling.",
                        "Realizing a $12B gain triggers massive capital gains tax, and redeploying that capital into a business of comparable quality is extraordinarily difficult. The friction cost of switching is high.",
                        "Value investors hold forever regardless of price — that is the core philosophy.",
                        "Selling was restricted by Berkshire's regulatory disclosure obligations to the SEC."
                    ],
                    zh: [
                        "巴菲特被锚定于成本基础——这是一种阻止理性卖出的典型心理偏差。",
                        "实现120亿美元收益将触发巨额资本利得税，且将资金再配置至同等质量业务的难度极高。切换的摩擦成本是真实存在的。",
                        "价值投资者永远持有，无论价格如何——这是核心理念。",
                        "出售受到伯克希尔向美国证券交易委员会披露义务的监管限制。"
                    ]
                },
                correct: 1,
                insight: {
                    en: "The hidden friction in selling great businesses is enormous. Capital gains tax on a 10× gain means receiving only ~75 cents per dollar sold. You must then find a business of comparable quality to redeploy into — an extremely rare thing. \"Our favorite holding period is forever\" is not sentimentality. It is the deliberate recognition that activity has tax and opportunity costs, and that inaction with a great business is itself an active strategy.",
                    zh: '卖出优质企业的隐性摩擦成本巨大。对10倍收益征收资本利得税意味着每出售1美元仅能获得约0.75美元。此后你还必须找到同等质量的企业来重新配置资金——这是极其罕见的事。"我们最喜欢的持有期是永远"并非情感化表达，而是对行动产生税收和机会成本的深思熟虑，以及对持有优质企业本身就是一种主动策略的清醒认知。'
                },
                attribution: {
                    en: 'Buffett, 1988 Letter: "When we own portions of outstanding businesses... our favorite holding period is forever."',
                    zh: '巴菲特，1988年致股东信："当我们持有优秀企业的股份时……我们最喜欢的持有期是永远。"'
                }
            }
        ]
    },

    'sees-candies': {
        title:    { en: "See's Candies, 1972",                  zh: '喜诗糖果，1972年' },
        year:     '1972',
        subtitle: { en: 'The Investment That Changed Everything', zh: '改变一切的那笔投资' },
        steps: [
            {
                theme: { en: 'Price vs. Value', zh: '价格与价值' },
                context: {
                    en: "It's 1972. Buffett is offered See's Candies for $25 million — roughly 3× book value. His Graham-trained instinct says never pay more than book. Charlie Munger pushes back: \"Warren, that's a wonderful business.\" See's earned $4.2M pre-tax on $8M of net tangible assets — a 52% return on capital.",
                    zh: '1972年，巴菲特获得以2500万美元收购喜诗糖果的机会——约为账面价值的3倍。他受格雷厄姆培训的直觉告诉他，决不能支付超过账面价值的价格。合伙人查理·芒格强烈反驳："沃伦，那是一家了不起的企业。"喜诗以800万美元净有形资产创造了420万美元税前利润——52%的资本回报率。'
                },
                question: {
                    en: "Why was paying 3× book value rational for See's Candies?",
                    zh: "为什么支付3倍账面价值买入喜诗糖果是理性的？"
                },
                options: {
                    en: [
                        "Book value understated real estate — See's owned prime California retail locations worth far more than recorded.",
                        "The real asset was brand loyalty and pricing power, invisible on the balance sheet. Earnings power was the correct lens, not asset value.",
                        "3× book was still cheap because comparable candy companies traded at 5× book on average.",
                        "Buffett miscalculated and later admitted he significantly overpaid for See's."
                    ],
                    zh: [
                        "账面价值低估了房产价值——喜诗拥有加州核心地段的零售物业，价值远超账面记录。",
                        "真正的资产是品牌忠诚度和定价权，这些在资产负债表上看不见。盈利能力才是正确的分析维度，而非资产价值。",
                        "3倍账面价值仍然便宜，因为可比糖果公司平均以5倍账面价值交易。",
                        "巴菲特计算有误，后来承认为喜诗支付了过高的价格。"
                    ]
                },
                correct: 1,
                insight: {
                    en: "See's taught Buffett that the most valuable assets in great businesses don't appear on balance sheets: brand loyalty, customer habits, pricing power. The relevant question wasn't 'what are the assets worth at liquidation?' — it was 'what will this earnings engine produce over the next 20 years?' Munger's insistence on this forced a permanent upgrade to Buffett's framework.",
                    zh: '喜诗教会了巴菲特：优质企业中最有价值的资产往往在资产负债表上看不见——品牌忠诚度、客户习惯、定价权。关键问题不是"资产清算价值是多少"，而是"这台盈利机器未来20年会产生什么收益"。芒格对此的坚持，迫使巴菲特对自己的投资框架进行了永久性的升级。'
                },
                attribution: {
                    en: 'Buffett, 2007 Letter: "Charlie shoved me in the direction of thinking about durable competitive advantage."',
                    zh: '巴菲特，2007年致股东信："查理推动我开始思考持久竞争优势。"'
                }
            },
            {
                theme: { en: 'Pricing Power', zh: '定价权' },
                context: {
                    en: "Each year at Christmas, See's would raise its prices. Customers complained — and then bought anyway. Between 1972 and 2007, prices rose from roughly $1.95/lb to $11.50/lb, a 6× increase. Volume barely changed. No customer left for a cheaper alternative on Valentine's Day.",
                    zh: "每年圣诞节，喜诗都会提价。顾客投诉——然后还是照买不误。1972年至2007年间，价格从约1.95美元/磅涨至11.50美元/磅，涨幅达6倍。销量几乎没有下降。在情人节，没有顾客因为更便宜的替代品而离开。"
                },
                question: {
                    en: "What does See's annual pricing power reveal about its competitive position?",
                    zh: "喜诗每年的定价权揭示了其什么样的竞争地位？"
                },
                options: {
                    en: [
                        "See's competed on cost — it was the low-price leader in premium chocolate.",
                        "The business had no real pricing power; Buffett simply got lucky with inflation.",
                        "Pricing power without volume loss is the definitive test of a brand moat — customers value the emotional experience more than the incremental cost.",
                        "See's benefited from a lack of competition because artisan chocolate is an inherently niche market."
                    ],
                    zh: [
                        "喜诗依靠成本竞争——它是高端巧克力中的低价领导者。",
                        "该业务没有真正的定价权；巴菲特只是借助通胀获得了运气。",
                        "不损失销量的定价权是品牌护城河的终极测验——顾客对情感体验的重视程度超过了价格增量。",
                        "喜诗受益于缺乏竞争，因为手工巧克力本身就是一个小众市场。"
                    ]
                },
                correct: 2,
                insight: {
                    en: "Buffett called See's the 'prototype of a dream business.' The ability to raise prices annually — with customers complaining but not leaving — is the clearest real-world proof of brand moat. The product carries emotional weight that transcends price. Buffett estimated that for every $1 of price increase, roughly $0.70 fell to the bottom line. That is pricing power made tangible.",
                    zh: '巴菲特称喜诗是"梦想企业的原型"。每年提价——顾客投诉但不离去——是品牌护城河最清晰的现实验证。产品具有超越价格的情感意义。巴菲特估计，每提价1美元，约有0.70美元流入净利润——这就是定价权的具体体现。'
                },
                attribution: {
                    en: "Buffett, 1983 Letter: \"The ability to raise prices... without losing business to a competitor is a great business to own.\"",
                    zh: '巴菲特，1983年致股东信："无需失去客户就能提价的能力……是拥有一家优秀企业的标志。"'
                }
            },
            {
                theme: { en: 'Capital Efficiency', zh: '资本效率' },
                context: {
                    en: "Between 1972 and 2011, See's grew pre-tax earnings from $4.2M to over $80M — nearly 20×. The cumulative incremental capital required to fund that entire growth was only $32M above the original investment. Every year, the remainder was paid out to Berkshire to deploy elsewhere.",
                    zh: "1972年至2011年间，喜诗税前利润从420万美元增长至逾8000万美元——接近20倍。在此期间，支撑这一全部增长所需的累计增量资本，仅比原始投资多出3200万美元。每年剩余利润均被支付给伯克希尔，由巴菲特配置至其他投资。"
                },
                question: {
                    en: "What is the investment significance of See's minimal capital requirements?",
                    zh: "喜诗极低的资本需求有何投资意义？"
                },
                options: {
                    en: [
                        "Low capex means See's couldn't grow — a capital-light business is inherently limited in scale.",
                        "See's freed up cash for Buffett to deploy into higher-return investments. The business was a self-funding capital machine.",
                        "Low reinvestment needs meant See's was a slowly declining business in a maturing market.",
                        "See's saved capital by using cheap labor and deferring technology investment."
                    ],
                    zh: [
                        "低资本支出意味着喜诗无法增长——轻资产企业在规模上天然受限。",
                        "喜诗将现金释放出来，供巴菲特配置至更高回报的投资。这家企业是一台自我供给的资本机器。",
                        "低再投资需求意味着喜诗是一家在萎缩市场中缓慢衰退的企业。",
                        "喜诗通过使用廉价劳动力和推迟技术投资来节省资本。"
                    ]
                },
                correct: 1,
                insight: {
                    en: "See's is Buffett's clearest illustration of capital-light compounding. The business required almost no incremental capital to grow earnings 20×. Every dollar it didn't reinvest was extracted and redeployed. By 2011, cumulative pre-tax earnings exceeded $1.65 billion on a $25M original investment — funding countless subsequent Berkshire acquisitions.",
                    zh: "喜诗是巴菲特对轻资产复利最清晰的阐释。几乎不需要增量资本，利润就增长了20倍。每一个不需要再投入的美元都被提取出来重新配置。到2011年，喜诗的累计税前利润已超过16.5亿美元，而原始投资仅为2500万美元——为伯克希尔此后无数次收购提供了资金来源。"
                },
                attribution: {
                    en: 'Buffett, 2012 Letter: "The $25 million we paid for See\'s in 1972 has produced $1.65 billion in pre-tax earnings over 40 years."',
                    zh: '巴菲特，2012年致股东信："1972年我们为喜诗支付的2500万美元，在40年间产生了16.5亿美元的税前收益。"'
                }
            },
            {
                theme: { en: 'The Framework Shift', zh: '框架转变' },
                context: {
                    en: "Before See's, Buffett's primary model came from Ben Graham: buy assets cheaply and sell when the gap closes. After See's, he began shifting: buy businesses with durable earnings power and hold indefinitely. The cigar-butt approach found value in distress; the See's approach found it in enduring quality.",
                    zh: "在喜诗之前，巴菲特的主要思维模型来自本·格雷厄姆：廉价买入资产，待价差消除后卖出。喜诗之后，他开始转变：买入具有持久盈利能力的企业，无限期持有。烟蒂式投资在困境资产中寻找价值；喜诗式投资则在持久品质中寻找价值。"
                },
                question: {
                    en: "What was the fundamental intellectual shift See's Candies triggered in Buffett's investment framework?",
                    zh: "喜诗糖果在巴菲特投资框架中触发了怎样的根本性思维转变？"
                },
                options: {
                    en: [
                        "Buffett became less interested in downside protection after See's, preferring high-growth companies.",
                        "See's validated Graham's approach — it was simply a cigar-butt at an unusually high quality tier.",
                        "From 'what are the assets worth at liquidation?' to 'what will this business earn over 20+ years?' — a shift from balance sheet to earnings power as the primary lens.",
                        "Buffett learned to focus on book value growth rather than market price, which is the correct long-term metric."
                    ],
                    zh: [
                        "喜诗之后，巴菲特对下行保护的兴趣减少了，转而偏好高增长公司。",
                        "喜诗验证了格雷厄姆的方法——它只是在质量层面异常高的一根烟蒂。",
                        '从"清算时资产值多少"到"这家企业未来20年以上能赚多少"——从资产负债表到盈利能力的根本性视角转换。',
                        "巴菲特学会了关注账面价值增长而非市场价格，后者才是正确的长期衡量指标。"
                    ]
                },
                correct: 2,
                insight: {
                    en: "See's permanently altered how Buffett evaluated businesses. Graham's framework was designed for a world where great businesses were rare and cheap assets abundant. Munger's influence, crystallized by See's, reoriented the core question: don't ask what it's worth today — ask what the earnings engine produces over two decades. This shift compounded into every major investment afterward, from Coca-Cola to Apple.",
                    zh: "喜诗永久改变了巴菲特评估企业的方式。格雷厄姆的框架是为一个优质企业稀缺、廉价资产充裕的世界设计的。芒格的影响，通过喜诗而得以具象化，重新定位了核心问题：不要问今天值多少钱——而要问这台盈利引擎在未来二十年能产生什么。这一转变，复利进入了之后的每一项重要投资，从可口可乐到苹果。"
                },
                attribution: {
                    en: "Buffett, 1992 Letter: \"It's far better to buy a wonderful company at a fair price than a fair company at a wonderful price.\"",
                    zh: '巴菲特，1992年致股东信："以合理价格买入优秀企业，远胜于以优惠价格买入平庸企业。"'
                }
            }
        ]
    }
};

// ─── Language Functions ────────────────────────────────────────
function toggleLang() {
    setLang(currentLang === 'zh' ? 'en' : 'zh');
}

function setLang(lang) {
    currentLang = lang;
    localStorage.setItem('lang', lang);
    document.querySelectorAll('.lang-toggle').forEach(btn => {
        btn.textContent = lang === 'zh' ? 'EN' : '中文';
    });
    applyLang();
}

function applyLang() {
    const L = LANG[currentLang];

    // Home view
    const h = document.getElementById('home-headline');
    if (h) h.textContent = L.headline;
    const sh = document.getElementById('home-subheadline');
    if (sh) sh.textContent = L.subheadline;
    const cqt = document.getElementById('home-card-qa-title');
    if (cqt) cqt.textContent = L.cardQaTitle;
    const cqd = document.getElementById('home-card-qa-desc');
    if (cqd) cqd.textContent = L.cardQaDesc;
    const cqc = document.getElementById('home-card-qa-cta');
    if (cqc) cqc.textContent = L.cardQaCta;
    const ctt = document.getElementById('home-card-train-title');
    if (ctt) ctt.textContent = L.cardTrainTitle;
    const ctd = document.getElementById('home-card-train-desc');
    if (ctd) ctd.textContent = L.cardTrainDesc;
    const ctc = document.getElementById('home-card-train-cta');
    if (ctc) ctc.textContent = L.cardTrainCta;
    const fl = document.getElementById('home-footer-line');
    if (fl) fl.textContent = L.footerLine;

    // Pre-chat
    const pct = document.getElementById('pre-chat-title');
    if (pct) pct.textContent = L.preChatTitle;
    const pci = document.getElementById('pre-chat-input');
    if (pci) pci.placeholder = L.preChatPlaceholder;

    // Suggestion chips — regenerate
    const sugEl = document.querySelector('.pre-chat-suggestions');
    if (sugEl) {
        sugEl.innerHTML = L.suggestions.map(s =>
            `<button class="suggestion-chip" onclick="sendSuggestion('${s.replace(/'/g, "\\'")}')">${s}</button>`
        ).join('');
    }

    // Chat view
    document.querySelectorAll('.brand-text').forEach(el => { el.textContent = L.brandText; });
    const csi = document.getElementById('chat-search-input');
    if (csi) csi.placeholder = L.chatPlaceholder;
    document.querySelectorAll('.new-chat-btn').forEach(btn => { btn.textContent = L.newChat; });
    const st = document.getElementById('sidebar-title');
    if (st) st.textContent = L.sidebarSourceTitle;

    // Training
    document.querySelectorAll('.training-back-btn').forEach(btn => { btn.textContent = L.trainingBack; });
}

// ─── Core state ────────────────────────────────────────────────
function enterChatMode() {
    if (hasStartedChat) return;
    hasStartedChat = true;
    const preChatEl = document.getElementById('pre-chat');
    preChatEl.style.opacity = '0';
    preChatEl.style.pointerEvents = 'none';
    setTimeout(() => {
        document.getElementById('chat-main').classList.add('chat-started');
    }, 300);
}

function sendSuggestion(text) {
    if (isGenerating) return;
    sendQuery(text);
}

function isNearBottom(el) {
    return el.scrollHeight - el.scrollTop - el.clientHeight < 80;
}

function scrollToBottom(el) {
    if (isNearBottom(el)) {
        el.scrollTop = el.scrollHeight;
    }
}

function scrollToBottomIfNeeded() {
    if (userScrolledUp) return;
    const el = document.getElementById('chat-history');
    if (el) el.scrollTop = el.scrollHeight;
}

function switchToChatView() {
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('chat-view').style.display = 'flex';
}

// ─── Sidebar ───────────────────────────────────────────────────
function openSidebar(idx, num) {
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('sidebar-content');
    const title = document.getElementById('sidebar-title');

    const source = lastSources[idx];
    if (!source) return;

    title.textContent = `${LANG[currentLang].sidebarSourceTitle} [${num}]`;

    let metaHtml = `<div class="sidebar-source-meta">
        <strong>Source:</strong> ${source.label}<br>
        <strong>Section:</strong> ${source.section || 'N/A'}<br>
        ${source.year ? `<strong>Year:</strong> ${source.year}<br>` : ''}
        ${source.url ? `<a href="${source.url}" target="_blank" style="color: #1a73e8; text-decoration: none; margin-top: 8px; display: inline-block;">View on CNBC Archive ↗</a>` : ''}
    </div>`;

    let displayText = source.text;
    if (source.full_context) {
        const escapeRegExp = (string) => string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const searchPattern = new RegExp(escapeRegExp(source.text), 'g');
        if (searchPattern.test(source.full_context)) {
            displayText = source.full_context.replace(searchPattern, `<span class="highlight-quote">$&</span>`);
        } else {
            displayText = source.full_context;
        }
    } else {
        displayText = `<span class="highlight-quote">${source.text}</span>`;
    }

    let paragraphs = displayText.replace(/\r/g, '').split(/\n\s*\n/);
    paragraphs = paragraphs.map(p => {
        return p.split('\n').map(line => line.trim()).filter(line => line.length > 0).join(' ');
    }).filter(p => p.length > 0);
    displayText = paragraphs.map(p => `<p>${p}</p>`).join('');

    content.innerHTML = metaHtml + `<div class="source-text">${displayText}</div>`;
    sidebar.classList.add('active');

    setTimeout(() => {
        const highlight = content.querySelector('.highlight-quote');
        if (highlight) highlight.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 350);
}

function closeSidebar() {
    document.getElementById('sidebar').classList.remove('active');
}

// ─── Citations ─────────────────────────────────────────────────
function formatCitations(html, sources) {
    if (sources) lastSources = sources;

    let normalizedHtml = html.replace(/(?:\[(?:来源|Sources?)\s*([\d\s,、]+)\][\s,、]*)+/ig, (match) => {
        let nums = [];
        let r = /\[(?:来源|Sources?)\s*([\d\s,、]+)\]/ig;
        let m;
        while ((m = r.exec(match)) !== null) {
            let parts = m[1].split(/[,、\s]+/).map(n => parseInt(n)).filter(n => !isNaN(n));
            nums.push(...parts);
        }
        nums = [...new Set(nums)];
        return `[来源${nums.join(',')}]`;
    });

    return normalizedHtml.replace(/\[(?:来源|Sources?)\s*([\d\s,、]+)\]/ig, (match, p1) => {
        const nums = p1.split(/[,、\s]+/).map(n => parseInt(n)).filter(n => !isNaN(n));
        if (nums.length === 0) return match;

        const createTag = (num) => {
            const idx = num - 1;
            const source = sources && sources[idx];
            let tooltipHtml = '';
            let label = '';
            if (source) {
                // Build short label: "巴菲特 1993" / "芒格" / "Marks 2013" etc.
                const authorShort = (source.author || '').split(',')[0].trim()
                    .replace('Warren Buffett', '巴菲特')
                    .replace('Charlie Munger', '芒格')
                    .replace('Howard Marks', 'Marks')
                    .replace('Li Lu', '李录');
                const yearPart = source.year ? ` ${source.year}` : '';
                label = authorShort ? `${authorShort}${yearPart}` : String(num);

                let safeText = source.text.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                const safeLabel = source.label.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                tooltipHtml = `
                    <div class="cite-tooltip">
                        <div class="cite-text">"${safeText}"</div>
                        <div class="cite-meta">${safeLabel}${source.year ? ` • ${source.year}` : ''}</div>
                    </div>`;
            } else {
                label = String(num);
                tooltipHtml = `
                    <div class="cite-tooltip">
                        <div class="cite-text">Detailed source text for this citation is currently unavailable in the local cache.</div>
                        <div class="cite-meta">Reference [Source ${num}]</div>
                    </div>`;
            }
            return `<span class="cite-tag" onclick="event.stopPropagation(); openSidebar(${idx}, ${num})">
                <span class="cite-num">${label}</span>
                ${tooltipHtml}
            </span>`;
        };

        if (nums.length === 1) {
            return `<span class="cite-group">${createTag(nums[0])}</span>`;
        } else {
            let firstTag = createTag(nums[0]);
            let hiddenTags = nums.slice(1).map(createTag).join('');
            return `<span class="cite-group">
                ${firstTag}
                <span class="cite-ellipsis" onclick="this.parentElement.classList.add('expanded'); event.stopPropagation();">···</span>
                <span class="cite-hidden">${hiddenTags}</span>
            </span>`;
        }
    });
}

// ─── Message rendering ─────────────────────────────────────────
function renderMessage(role, content, sources = null, searchParams = null) {
    const historyDiv = document.getElementById('chat-history');
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    if (role === 'user') {
        bubble.textContent = content;
    } else {
        if (searchParams) {
            let intentHtml = `<div class="search-intent-status">
                <span>🔍 Search Intent:</span>
                <span class="intent-tag">Keywords: ${searchParams.query}</span>
                ${searchParams.year ? `<span class="intent-tag">Year: ${searchParams.year}</span>` : ''}
                ${searchParams.doc_type ? `<span class="intent-tag">Type: ${searchParams.doc_type.replace('_', ' ')}</span>` : ''}
            </div>`;
            bubble.innerHTML = intentHtml + '<div class="answer-text"></div>';
        } else {
            bubble.innerHTML = '<div class="answer-text">' + formatCitations(marked.parse(content), sources) + '</div>';
        }
    }

    row.appendChild(bubble);
    historyDiv.appendChild(row);
    scrollToBottom(historyDiv);
    return bubble;
}

function showLoading() {
    const historyDiv = document.getElementById('chat-history');
    const row = document.createElement('div');
    row.className = 'message-row assistant loading-row';
    row.id = 'loading-indicator';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerHTML = `<div class="loading-spinner"><div class="dot-flashing"></div><span style="margin-left:16px">${LANG[currentLang].loadingText}</span></div>`;

    row.appendChild(bubble);
    historyDiv.appendChild(row);
    scrollToBottom(historyDiv);
}

function removeLoading() {
    const indicator = document.getElementById('loading-indicator');
    if (indicator) indicator.remove();
}

// ─── Generation control ────────────────────────────────────────
let currentAbortController = null;

const sendSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
    <line x1="12" y1="19" x2="12" y2="5"></line>
    <polyline points="5 12 12 5 19 12"></polyline>
</svg>`;

const stopSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="#fff" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <rect x="6" y="6" width="12" height="12" rx="2" ry="2"></rect>
</svg>`;

function stopGeneration() {
    if (currentAbortController) {
        currentAbortController.abort();
        currentAbortController = null;
    }
    isGenerating = false;
    updateButtonsState();
    removeLoading();
}

function updateButtonsState() {
    const homeBtn = document.getElementById('home-submit-btn');
    const chatBtn = document.getElementById('chat-submit-btn');
    const homeInput = document.getElementById('home-search-input');
    const chatInput = document.getElementById('chat-search-input');

    if (isGenerating) {
        homeBtn.innerHTML = stopSvg;
        chatBtn.innerHTML = stopSvg;
        homeBtn.classList.add('active', 'stop-mode');
        chatBtn.classList.add('active', 'stop-mode');
    } else {
        homeBtn.innerHTML = sendSvg;
        chatBtn.innerHTML = sendSvg;
        homeBtn.classList.remove('stop-mode');
        chatBtn.classList.remove('stop-mode');

        if (homeInput.value.trim().length > 0) homeBtn.classList.add('active');
        else homeBtn.classList.remove('active');

        if (chatInput.value.trim().length > 0) chatBtn.classList.add('active');
        else chatBtn.classList.remove('active');
    }
}

// ─── sendQuery (SSE streaming) ─────────────────────────────────
function createAssistantBubble(searchParams) {
    const historyDiv = document.getElementById('chat-history');
    const row = document.createElement('div');
    row.className = 'message-row assistant';
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    let intentHtml = '';
    if (searchParams) {
        intentHtml = `<div class="search-intent-status">
            <span>🔍 Search Intent:</span>
            <span class="intent-tag">Keywords: ${searchParams.query}</span>
            ${searchParams.year ? `<span class="intent-tag">Year: ${searchParams.year}</span>` : ''}
            ${searchParams.doc_type ? `<span class="intent-tag">Type: ${searchParams.doc_type.replace('_', ' ')}</span>` : ''}
        </div>`;
    }
    bubble.innerHTML = intentHtml + '<div class="answer-text"></div>';
    row.appendChild(bubble);
    historyDiv.appendChild(row);
    scrollToBottomIfNeeded();
    return { bubble, container: bubble.querySelector('.answer-text') };
}

async function sendQuery(queryText) {
    if (!queryText.trim() || isGenerating) return;
    enterChatMode();
    isGenerating = true;
    userScrolledUp = false;
    updateButtonsState();

    switchToChatView();

    document.getElementById('home-search-input').value = '';
    document.getElementById('chat-search-input').value = '';

    renderMessage('user', queryText);
    showLoading();

    currentAbortController = new AbortController();

    let assistantBubble = null;
    let answerContainer = null;
    let accText = '';
    let finalSources = null;
    let rafPending = false;

    function scheduleRender() {
        if (rafPending) return;
        rafPending = true;
        requestAnimationFrame(() => {
            rafPending = false;
            if (answerContainer) {
                answerContainer.innerHTML = formatCitations(marked.parse(accText), finalSources) +
                    '<span class="typing-cursor"></span>';
                scrollToBottomIfNeeded();
            }
        });
    }

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: queryText, history: chatHistory }),
            signal: currentAbortController.signal
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const parts = buffer.split('\n\n');
            buffer = parts.pop();

            for (const chunk of parts) {
                if (!chunk.startsWith('data: ')) continue;
                const jsonStr = chunk.slice(6).trim();
                if (!jsonStr) continue;

                let event;
                try { event = JSON.parse(jsonStr); } catch { continue; }

                if (event.type === 'searching') {
                    // Loading indicator already shown
                } else if (event.type === 'token') {
                    // Remove loading indicator on first token
                    removeLoading();
                    // Create bubble on first token
                    if (!assistantBubble) {
                        const created = createAssistantBubble(null);
                        assistantBubble = created.bubble;
                        answerContainer = created.container;
                    }
                    accText += event.text;
                    scheduleRender();
                } else if (event.type === 'done') {
                    removeLoading();
                    finalSources = event.sources;

                    if (!assistantBubble) {
                        // No tokens streamed (shouldn't happen) — render full
                        const created = createAssistantBubble(event.search_params);
                        assistantBubble = created.bubble;
                        answerContainer = created.container;
                    } else if (event.search_params) {
                        // Inject search params header above answer
                        const sp = event.search_params;
                        const intentHtml = `<div class="search-intent-status">
                            <span>🔍 Search Intent:</span>
                            <span class="intent-tag">Keywords: ${sp.query}</span>
                            ${sp.year ? `<span class="intent-tag">Year: ${sp.year}</span>` : ''}
                            ${sp.doc_type ? `<span class="intent-tag">Type: ${sp.doc_type.replace('_', ' ')}</span>` : ''}
                        </div>`;
                        assistantBubble.insertAdjacentHTML('afterbegin', intentHtml);
                    }

                    // Final render — no cursor
                    const finalText = event.final_answer || accText;
                    answerContainer.innerHTML = formatCitations(marked.parse(finalText), event.sources);

                    chatHistory.push({ role: 'user', content: queryText });
                    chatHistory.push({ role: 'assistant', content: finalText });

                    if (event.follow_ups && event.follow_ups.length > 0) {
                        const fuRow = document.createElement('div');
                        fuRow.className = 'message-row assistant';
                        const wrap = document.createElement('div');
                        wrap.style.cssText = 'display:flex;flex-direction:column;gap:8px;margin-top:12px;align-items:flex-start;max-width:100%;';
                        event.follow_ups.forEach(fq => {
                            const btn = document.createElement('button');
                            btn.className = 'chip';
                            btn.style.cssText = 'text-align:left;height:auto;padding:10px 16px;';
                            btn.textContent = fq;
                            btn.addEventListener('click', () => submitChatQuery(fq));
                            wrap.appendChild(btn);
                        });
                        fuRow.appendChild(wrap);
                        document.getElementById('chat-history').appendChild(fuRow);
                    }

                    isGenerating = false;
                    updateButtonsState();
                    scrollToBottomIfNeeded();
                } else if (event.type === 'error') {
                    removeLoading();
                    renderMessage('assistant', `**Error:** ${event.message}`);
                    isGenerating = false;
                    updateButtonsState();
                }
            }
        }
    } catch (error) {
        removeLoading();
        if (error.name !== 'AbortError') {
            renderMessage('assistant', `**Network Error:** Could not reach the server.`);
        } else if (answerContainer && accText) {
            // User aborted — show partial answer without cursor
            answerContainer.innerHTML = formatCitations(marked.parse(accText), finalSources);
        }
        isGenerating = false;
        updateButtonsState();
    }
}

function submitHomeQuery(text) {
    if (isGenerating) return;
    sendQuery(text);
}

function submitChatQuery(text) {
    if (isGenerating) return;
    if (!text) text = document.getElementById('chat-search-input').value;
    sendQuery(text);
}

function handleBtnClick(inputId) {
    if (isGenerating) {
        stopGeneration();
    } else {
        const val = document.getElementById(inputId).value;
        if (val.trim().length > 0) sendQuery(val);
    }
}

// ─── New Chat / Home ────────────────────────────────────────────
function newChat() {
    if (isGenerating) stopGeneration();
    chatHistory = [];
    lastSources = [];
    hasStartedChat = false;

    document.getElementById('chat-history').innerHTML = '';
    document.getElementById('chat-main').classList.remove('chat-started');

    const preChatEl = document.getElementById('pre-chat');
    preChatEl.style.opacity = '';
    preChatEl.style.pointerEvents = '';

    document.getElementById('chat-search-input').value = '';
    document.getElementById('pre-chat-input').value = '';
    closeSidebar();
    updateButtonsState();
    setTimeout(() => document.getElementById('pre-chat-input').focus(), 100);
}

function openChat() {
    switchToChatView();
    setTimeout(() => document.getElementById('pre-chat-input').focus(), 100);
}

// ─── Event listeners ────────────────────────────────────────────
document.getElementById('home-search-input').addEventListener('input', (e) => {
    if (isGenerating) return;
    const btn = document.getElementById('home-submit-btn');
    if (e.target.value.trim().length > 0) btn.classList.add('active');
    else btn.classList.remove('active');
});
document.getElementById('home-search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim().length > 0) {
        if (!isGenerating) sendQuery(e.target.value);
    }
});
document.getElementById('home-submit-btn').addEventListener('click', () => handleBtnClick('home-search-input'));

document.getElementById('chat-search-input').addEventListener('input', (e) => {
    if (isGenerating) return;
    const btn = document.getElementById('chat-submit-btn');
    if (e.target.value.trim().length > 0) btn.classList.add('active');
    else btn.classList.remove('active');
});
document.getElementById('chat-search-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim().length > 0) {
        if (!isGenerating) sendQuery(e.target.value);
    }
});
document.getElementById('chat-submit-btn').addEventListener('click', () => handleBtnClick('chat-search-input'));

document.getElementById('pre-chat-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && e.target.value.trim()) sendQuery(e.target.value);
});
document.getElementById('pre-chat-submit-btn').addEventListener('click', () => {
    const val = document.getElementById('pre-chat-input').value;
    if (val.trim()) sendQuery(val);
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
});

// Smart scroll: track if user has scrolled up during generation
document.getElementById('chat-history').addEventListener('scroll', () => {
    const el = document.getElementById('chat-history');
    userScrolledUp = (el.scrollHeight - el.scrollTop - el.clientHeight) > 150;
});

// File upload
document.querySelectorAll('.plus-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.getElementById('file-upload').click();
    });
});
document.getElementById('file-upload').addEventListener('change', (e) => {
    const files = e.target.files;
    if (files.length > 0) {
        const fileNames = Array.from(files).map(f => f.name).join(', ');
        alert(`You selected: ${fileNames}\n(File upload backend logic to be implemented)`);
    }
});

// ─── Training Mode ─────────────────────────────────────────────
let trainingState = {
    caseId: null,
    step: 0,
    selected: null,
    answers: []
};

function showCaseSelector() {
    switchToTrainingView();
    document.getElementById('training-step-label').textContent = '';
    document.getElementById('training-progress-fill').style.width = '0%';

    const L = LANG[currentLang];
    const casesHtml = Object.entries(TRAINING_CASES).map(([id, c]) => `
        <button class="case-item" onclick="startTraining('${id}')">
            <div class="case-item-year">${c.year || ''}</div>
            <div class="case-item-info">
                <div class="case-item-title">${c.title[currentLang]}</div>
                <div class="case-item-desc">${c.subtitle[currentLang]}</div>
            </div>
            <div class="case-item-meta">${c.steps.length} steps</div>
            <span class="case-item-arrow">→</span>
        </button>
    `).join('');

    document.getElementById('training-body').innerHTML = `
        <div class="case-selector">
            <div class="case-selector-header">
                <div class="case-selector-label">${L.caseSelectorLabel}</div>
                <div class="case-selector-sub">${L.caseSelectorSub}</div>
            </div>
            <div class="case-list">${casesHtml}</div>
        </div>
    `;
}

function startTraining(caseId) {
    trainingState = { caseId, step: 0, selected: null, answers: [] };
    switchToTrainingView();
    renderTrainingStep();
}

function switchToTrainingView() {
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('chat-view').style.display = 'none';
    document.getElementById('training-view').style.display = 'flex';
}

function exitTraining() {
    document.getElementById('training-view').style.display = 'none';
    document.getElementById('home-view').style.display = 'flex';
}

function exitTrainingToChat() {
    document.getElementById('training-view').style.display = 'none';
    document.getElementById('home-view').style.display = 'none';
    document.getElementById('chat-view').style.display = 'flex';
    setTimeout(() => document.getElementById('pre-chat-input').focus(), 100);
}

function renderTrainingStep() {
    const caseData = TRAINING_CASES[trainingState.caseId];
    const steps = caseData.steps;
    const stepData = steps[trainingState.step];
    const total = steps.length;
    const current = trainingState.step + 1;
    const L = LANG[currentLang];
    const lang = currentLang;

    document.getElementById('training-step-label').textContent = L.stepOf(current, total);
    document.getElementById('training-progress-fill').style.width = `${(current / total) * 100}%`;

    const optionsHtml = stepData.options[lang].map((opt, i) => `
        <button class="training-option" data-idx="${i}" onclick="selectTrainingOption(${i})">
            <span class="training-option-letter">${String.fromCharCode(65 + i)}</span>
            <span class="training-option-text">${opt}</span>
        </button>
    `).join('');

    document.getElementById('training-body').innerHTML = `
        <div class="training-step-card">
            <div class="training-theme-tag">${stepData.theme[lang]}</div>
            <div class="training-context">${stepData.context[lang]}</div>
            <div class="training-question">${stepData.question[lang]}</div>
            <div class="training-options">${optionsHtml}</div>
            <div class="training-insight" id="training-insight" style="display:none;">
                <div class="training-insight-label">${L.insightLabel}</div>
                <div class="training-insight-body">${stepData.insight[lang]}</div>
                ${stepData.attribution ? `<div class="training-attribution">${stepData.attribution[lang]}</div>` : ''}
            </div>
            <div class="training-actions" id="training-actions" style="display:none;">
                <button class="training-continue-btn" onclick="advanceTraining()">
                    ${trainingState.step < total - 1 ? L.continueBtn : L.summaryBtn}
                </button>
            </div>
        </div>
    `;

    document.getElementById('training-body').scrollTop = 0;
}

function selectTrainingOption(idx) {
    if (trainingState.selected !== null) return;
    trainingState.selected = idx;

    const stepData = TRAINING_CASES[trainingState.caseId].steps[trainingState.step];
    trainingState.answers.push({ step: trainingState.step, selected: idx, correct: stepData.correct });

    document.querySelectorAll('.training-option').forEach((btn, i) => {
        btn.disabled = true;
        if (i === stepData.correct) {
            btn.classList.add('training-option--correct');
        } else if (i === idx) {
            btn.classList.add('training-option--other');
        } else {
            btn.classList.add('training-option--dim');
        }
    });

    document.getElementById('training-insight').style.display = 'block';
    document.getElementById('training-actions').style.display = 'flex';

    setTimeout(() => {
        document.getElementById('training-insight').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
}

function advanceTraining() {
    const steps = TRAINING_CASES[trainingState.caseId].steps;
    if (trainingState.step < steps.length - 1) {
        trainingState.step++;
        trainingState.selected = null;
        renderTrainingStep();
    } else {
        renderTrainingSummary();
    }
}

function renderTrainingSummary() {
    const caseData = TRAINING_CASES[trainingState.caseId];
    const answers = trainingState.answers;
    const matched = answers.filter(a => a.selected === a.correct).length;
    const total = caseData.steps.length;
    const L = LANG[currentLang];
    const lang = currentLang;

    document.getElementById('training-step-label').textContent = L.summaryComplete;
    document.getElementById('training-progress-fill').style.width = '100%';

    const rowsHtml = answers.map(a => {
        const step = caseData.steps[a.step];
        const isMatch = a.selected === a.correct;
        return `
            <div class="summary-row ${isMatch ? 'summary-row--match' : 'summary-row--diff'}">
                <div class="summary-row-theme">${step.theme[lang]}</div>
                <div class="summary-row-detail">
                    <span class="summary-your-pick">${L.yourAnswer}: ${step.options[lang][a.selected]}</span>
                    ${!isMatch ? `<span class="summary-buffett-pick">${L.buffettFramework}: ${step.options[lang][a.correct]}</span>` : ''}
                </div>
                <span class="summary-icon">${isMatch ? '✓' : '—'}</span>
            </div>
        `;
    }).join('');

    document.getElementById('training-body').innerHTML = `
        <div class="training-summary">
            <div class="summary-header">
                <div class="summary-case-label">${L.summaryCaseLabel}</div>
                <div class="summary-title">${caseData.title[lang]}</div>
                <div class="summary-score">${L.summaryScoreText(matched, total)}</div>
                <div class="summary-subtitle">${L.summarySubtitle}</div>
            </div>
            <div class="summary-rows">${rowsHtml}</div>
            <div class="summary-actions">
                <button class="training-continue-btn training-continue-btn--secondary" onclick="exitTraining()">${L.summaryActionBack}</button>
                <button class="training-continue-btn" onclick="exitTrainingToChat()">${L.summaryActionChat}</button>
            </div>
        </div>
    `;

    document.getElementById('training-body').scrollTop = 0;
}

// ─── Init ───────────────────────────────────────────────────────
// Apply language on load and sync toggle button labels
document.querySelectorAll('.lang-toggle').forEach(btn => {
    btn.textContent = currentLang === 'zh' ? 'EN' : '中文';
});
applyLang();
