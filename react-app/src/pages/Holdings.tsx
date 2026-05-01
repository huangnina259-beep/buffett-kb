import { useState, useEffect, useCallback } from 'react'

type HoldingsTab = 'overview' | 'memo' | 'business' | 'moat' | 'mgmt' | 'financials' | 'valuation' | 'watchlist' | 'log'

const TABS: { id: HoldingsTab; label: string }[] = [
  { id: 'overview', label: '概况' },
  { id: 'memo', label: '投资备忘录' },
  { id: 'business', label: '商业模式' },
  { id: 'moat', label: '护城河' },
  { id: 'mgmt', label: '管理层' },
  { id: 'financials', label: '财务数据' },
  { id: 'valuation', label: '估值测算' },
  { id: 'watchlist', label: '关注指标' },
  { id: 'log', label: '研究日志' },
]

// Dark theme style helpers
const s = {
  card: { background: '#0f0f0f', border: '1px solid #1e1e1e', borderRadius: 6, padding: '22px 24px', marginBottom: 20 } as React.CSSProperties,
  cardTitle: { fontFamily: "'Courier New', monospace", fontSize: 11, textTransform: 'uppercase' as const, letterSpacing: '0.12em', color: '#666', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 } as React.CSSProperties,
  sectionHeader: { fontSize: 18, fontWeight: 400, margin: '32px 0 16px', paddingBottom: 8, borderBottom: '1px solid #2a2a2a', letterSpacing: '-0.2px', color: '#e0d8c8' } as React.CSSProperties,
  prose: { fontSize: 14, color: '#999', lineHeight: 1.8 } as React.CSSProperties,
  metricCard: { background: '#141414', border: '1px solid #1e1e1e', borderRadius: 6, padding: '14px 16px' } as React.CSSProperties,
  metricLabel: { fontSize: 11, color: '#666', fontFamily: "'Courier New', monospace", textTransform: 'uppercase' as const, letterSpacing: '0.06em', marginBottom: 4 } as React.CSSProperties,
  metricValue: { fontSize: 22, color: '#e0d8c8', letterSpacing: '-0.5px' } as React.CSSProperties,
  metricSub: { fontSize: 11, color: '#666', marginTop: 2, fontFamily: "'Courier New', monospace" } as React.CSSProperties,
  up: { color: '#4ade80' },
  down: { color: '#f87171' },
  tag: { display: 'inline-block', padding: '2px 8px', borderRadius: 3, fontSize: 11, fontFamily: "'Courier New', monospace", textTransform: 'uppercase' as const, letterSpacing: '0.05em', marginRight: 4 } as React.CSSProperties,
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={s.card}>
      <div style={s.cardTitle}>
        <span style={{ display: 'block', width: 14, height: 1, background: '#333' }} />
        {title}
      </div>
      {children}
    </div>
  )
}

function FinTable({ headers, children }: { headers: string[]; children: React.ReactNode }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <thead>
        <tr>
          {headers.map((h, i) => (
            <th key={i} style={{
              textAlign: i > 0 ? 'right' : 'left', padding: '8px 10px',
              borderBottom: '1.5px solid #2a2a2a', fontFamily: "'Courier New', monospace",
              fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em',
              color: '#666', fontWeight: 400,
            }}>{h}</th>
          ))}
        </tr>
      </thead>
      <tbody>{children}</tbody>
    </table>
  )
}

function Td({ children, num, up, down, style: extraStyle }: {
  children: React.ReactNode; num?: boolean; up?: boolean; down?: boolean; style?: React.CSSProperties
}) {
  return (
    <td style={{
      padding: '9px 10px', borderBottom: '1px solid #1a1a1a', color: up ? '#4ade80' : down ? '#f87171' : '#999',
      fontFamily: (num || up || down) ? "'Courier New', monospace" : undefined,
      textAlign: (num || up || down) ? 'right' : undefined, verticalAlign: 'top',
      ...extraStyle,
    }}>{children}</td>
  )
}

// ── Overview Tab ──
function OverviewTab() {
  return (
    <>
      {/* Core thesis */}
      <div style={{ background: '#141414', color: '#e0d8c8', borderRadius: 6, padding: '20px 24px', marginBottom: 20 }}>
        <div style={{ fontFamily: "'Courier New', monospace", fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#4ade80', marginBottom: 8 }}>
          核心投资论点（2026.04 更新）
        </div>
        <div style={{ fontSize: 14, lineHeight: 1.7, color: '#b0a898' }}>
          下行有底，上行有期权。30.6亿总市值中16.8亿是现金，扣除后只用13.8亿买下年收入6.61亿、翻倍增长的全球化生意。PanCares人工胰腺预计2026年下半年获批，目前股价尚未对此定价——获批是赠送的惊喜，不是押注前提。微泰是国内唯一同时拥有CGM和贴敷式胰岛素泵的公司，数据飞轮正在加速。最大风险：三诺已进入英国/奥地利医保，欧洲竞争比半年前更激烈。
        </div>
      </div>

      {/* Metrics grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12, marginBottom: 20 }}>
        {[
          { label: '总市值（2026.04）', value: '30.6', unit: '亿', sub: '人民币，约HK$7.90/股' },
          { label: '账面现金', value: '16.8', unit: '亿', sub: '无长期债务，约HK$4.4/股' },
          { label: '扣现金业务价值', value: '13.8', unit: '亿', sub: 'EV/收入 ≈ 2x（极低）', isUp: true },
          { label: '2025年收入', value: '6.61', unit: '亿', sub: '+91.2% YoY', subUp: true },
          { label: '2025净利润', value: '3800', unit: '万+', isUp: true, sub: '首次扭亏为盈', subUp: true },
          { label: 'CGM收入占比', value: '58.2', unit: '%', sub: '2025H1，来源：中报第19页' },
          { label: '国际收入占比', value: '49', unit: '%', sub: '+218% (2025H1)', subUp: true },
          { label: '欧洲医保国家', value: '7', sub: 'LinX准入国家（2025年）' },
        ].map((m, i) => (
          <div key={i} style={s.metricCard}>
            <div style={s.metricLabel}>{m.label}</div>
            <div style={{ ...s.metricValue, ...(m.isUp ? s.up : {}) }}>{m.value}<span style={{ fontSize: 14 }}>{m.unit}</span></div>
            <div style={{ ...s.metricSub, ...(m.subUp ? s.up : {}) }}>{m.sub}</div>
          </div>
        ))}
      </div>

      {/* Safety margin */}
      <Card title="安全边际分析（李录逻辑）">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
          {[
            { label: '现金保护层', color: '#4ade80', text: '账面现金16.8亿 ÷ 总市值30.6亿 = 55%。即使业务归零，现金价值已覆盖超过一半市值。下行空间有限。' },
            { label: '业务实际成本', color: '#60a5fa', text: '扣现金后13.8亿，买下年收入6.61亿（+91%增速）的全球化生意。EV/收入约2倍，相对成熟期CGM公司历史8-15倍PS，折价明显。' },
            { label: '期权价值', color: '#fbbf24', text: 'PanCares人工胰腺2026年下半年预计获批，目前股价未计入。FDA美国市场审批中。两者任一突破 = 估值重塑催化剂。' },
          ].map((item, i) => (
            <div key={i} style={{ background: '#141414', borderRadius: 6, padding: 14 }}>
              <div style={{ fontSize: 11, fontFamily: "'Courier New', monospace", textTransform: 'uppercase', color: item.color, marginBottom: 6 }}>{item.label}</div>
              <div style={{ fontSize: 13, color: '#999', lineHeight: 1.8 }}>{item.text}</div>
            </div>
          ))}
        </div>
      </Card>

      {/* Buffett checklist */}
      <Card title="巴菲特检验清单">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { pass: true, bold: '能理解的生意', text: ' — 糖尿病监测+治疗器械，剃须刀+刀片模式，逻辑简单' },
            { pass: true, bold: '持久竞争优势', text: ' — 国内唯一CGM+贴敷泵，欧洲医保准入，患者数据锁定' },
            { pass: true, bold: '优秀且诚信的管理层', text: ' — 郑攀持股37%，硅谷背景，14年专注，2026年2月回购' },
            { pass: true, bold: '合理的价格', text: ' — 扣现金EV/收入约2x，相对CGM赛道历史估值显著折价' },
            { pass: false, bold: '长期利润潜力', text: ' — 路径清晰，但需收入到15-16亿才能到3亿净利润，约2028年' },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 13, color: '#999' }}>
              <span style={{ color: item.pass ? '#4ade80' : '#fbbf24', fontSize: 16 }}>{item.pass ? '✓' : '◑'}</span>
              <span><strong style={{ color: '#e0d8c8' }}>{item.bold}</strong>{item.text}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Key risks */}
      <Card title="关键风险（不可回避）">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {[
            { level: '极高', color: '#f87171', bg: '#3a1a1a', text: '三诺欧洲医保已有突破：已进入英国、奥地利医保目录，在瑞典、西班牙、意大利有招标中标，借助Menarini渠道覆盖20+国。2026年是竞争最关键一年。' },
            { level: '中', color: '#fbbf24', bg: '#2a2a1a', text: 'PanCares审批不确定：原计划2023年，已延迟3年。即便获批，商业化初期会带来销售费用大幅增加（16.8亿现金是战略缓冲）。' },
            { level: '中', color: '#fbbf24', bg: '#2a2a1a', text: '2型患者复购率低于预期（真实用户反馈）：患者在非调药期停用CGM，转而使用BGM试纸，导致CGM高频消耗的假设对2型患者不成立。' },
            { level: '中', color: '#fbbf24', bg: '#2a2a1a', text: 'NZ FIF税务成本：持仓超5万NZD触发FIF规则，按市值5%年度计税，长期持有成本不可忽视。' },
            { level: '低', color: '#666', bg: '#1a1a1a', text: '国内医疗反腐、集采政策波及院内渠道' },
          ].map((r, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 13, color: '#999' }}>
              <span style={{ ...s.tag, background: r.bg, color: r.color, border: `1px solid ${r.color}33`, flexShrink: 0 }}>{r.level}</span>
              <div>{r.text}</div>
            </div>
          ))}
        </div>
      </Card>
    </>
  )
}

// ── Memo Tab ──
function MemoTab() {
  return (
    <>
      <div style={s.sectionHeader}>投资备忘录（2026.04.21）</div>

      <div style={{ background: '#141414', borderRadius: 6, padding: '20px 24px', marginBottom: 20 }}>
        <div style={{ fontFamily: "'Courier New', monospace", fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#4ade80', marginBottom: 8 }}>核心结论</div>
        <div style={{ fontSize: 14, lineHeight: 1.7, color: '#b0a898' }}>
          这是一个"下行有底，上行有期权"的不对称机会。现有业务+现金储备已足够实惠，PanCares获批只是赠送的惊喜，不是押注前提。
        </div>
      </div>

      <Card title="一、核心估值：安全边际来自现金">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>实际价格（2026.04.21）：</strong>总市值约30.6亿人民币（实时股价约HK$7.90）。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>账面现金：</strong>约16.82亿人民币（来源：2025年报业绩公告）。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>实际业务收购价：</strong>约13.8亿人民币（总市值 - 净现金）。</p>
          <p><strong style={{ color: '#e0d8c8' }}>分析：</strong>目前市场价中近55%是现金。只用了不到14亿就买下了年营收6.61亿（且翻倍增长）的全球化生意。EV/收入约2倍，相对CGM龙头历史8-15倍PS显著折价。下行风险被现金储备锁定。</p>
        </div>
        <FinTable headers={['项目', '金额（亿人民币）', '备注']}>
          <tr><Td>总市值</Td><Td num>30.6</Td><Td style={{ fontSize: 12 }}>HK$7.90/股 × 4.2亿股 × 汇率</Td></tr>
          <tr><Td>账面现金</Td><Td up>16.82</Td><Td style={{ fontSize: 12 }}>来源：2025年中期报告第5页</Td></tr>
          <tr><Td>长期债务</Td><Td up>~0</Td><Td style={{ fontSize: 12 }}>无长期有息负债</Td></tr>
          <tr style={{ background: '#1a3a2a' }}><Td style={{ fontWeight: 700, color: '#e0d8c8' }}>业务实际价格（EV）</Td><Td up>~13.8</Td><Td style={{ fontSize: 12 }}>市场给业务本身的定价</Td></tr>
          <tr><Td>÷ 2025年收入</Td><Td num>6.61</Td><Td style={{ fontSize: 12 }}>来源：2026年2月业绩公告</Td></tr>
          <tr style={{ background: '#1a3a2a' }}><Td style={{ fontWeight: 700, color: '#e0d8c8' }}>EV / 收入（倍）</Td><Td up>~2.1x</Td><Td style={{ fontSize: 12 }}>相对历史估值极低</Td></tr>
        </FinTable>
      </Card>

      <Card title={'二、商业模式：从"卖仪器"到"卖耗材"'}>
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>剃须刀模式：</strong>CGM（持续血糖监测）收入占比已达58.2%（2025H1，来源：中报第19页）。传感器每7-14天消耗一次，形成高频稳定复购。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>用户粘性（转换成本）：</strong>长期用户的血糖历史数据沉淀在微泰APP，医生后台习惯了微泰的报告格式——切换品牌等于从头开始建档案，阻力随使用时间单调递增。</p>
          <p><strong style={{ color: '#e0d8c8' }}>真实用户补充（第一手反馈）：</strong>2型糖尿病患者在非调药期会停用CGM传感器，但仍持续使用BGM试纸和微泰APP。这说明两点：CGM的高频复购假设对2型患者不完全成立；但APP和试纸的持续使用维持了生态黏性，用户并没有真正离开。</p>
        </div>
        <div style={{ marginTop: 12, padding: '12px 14px', background: '#2a2a1a', borderLeft: '2px solid #fbbf24', borderRadius: '0 6px 6px 0', fontSize: 13, color: '#fbbf24' }}>
          ⚠️ 重要修正：备忘录初稿写CGM占比68.3%，经核实中报原文为58.2%（2025H1）。68.3%数字来源不明，不应使用。
        </div>
      </Card>

      <Card title="三、关键催化剂：PanCares（免费期权）">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>审批状态：</strong>已提交NMPA注册申请，预期2026年下半年获批。AiDEX和PanCares已获NMPA认定可适用"创新医疗器械特别审查程序"（来源：2025年中报第15页）。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>注意：</strong>"绿色通道"是创新医疗器械特别审查程序的通俗说法，意味着审批周期比常规缩短约一半，但不等于"一定获批"。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>逻辑：</strong>目前股价未对该产品定价。若获批，能将"阶段性调药用户"转化为"24小时佩戴的闭环用户"，大幅提升复购率，同时将微泰从CGM公司升级为"糖尿病管理平台"，对应更高的估值倍数。</p>
          <p><strong style={{ color: '#e0d8c8' }}>风险：</strong>原计划2023年推出，已延迟3年。获批后大规模推广会导致销售费用短期激增。16.8亿现金是这一阶段的战略缓冲。</p>
        </div>
      </Card>

      <Card title="四、真实风险：不可回避的几件事">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>三诺欧洲威胁已具体化（最大风险）：</strong>三诺已进入英国、奥地利国家医保目录，在瑞典、西班牙、意大利招标中标，借助Menarini渠道布局欧洲20+国。这不是"潜在竞争"，是正在发生的事。微泰仍有7国先发优势，但2026年竞争格局会发生实质改变。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>2型患者复购率低于假设（真实用户反馈）：</strong>CGM"高频消耗"的商业模式对1型患者成立，对2型患者是间歇性需求。中国糖尿病患者90%是2型，这限制了国内市场的CGM持续复购预期。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>集采与渠道风险：</strong>高利润依赖大医院渠道，若CGM被纳入集采，利润空间将受压缩。目前暂无具体信号，但需持续关注政策动向。</p>
          <p><strong style={{ color: '#e0d8c8' }}>NZ投资者特有税务成本：</strong>持仓超过NZD 5万触发FIF规则，每年按市值5%计税，无论是否盈利。3-5年持有期内这是真实的持有成本，需要计入回报预期。</p>
        </div>
      </Card>

      <Card title="五、操作框架与监控计划">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>持仓逻辑定位：</strong>基本面已确认扭亏且现金充沛，在30亿市值附近属于"左侧布局"区间，适合分批建仓而非一次性博弈。</p>
          <p><strong style={{ color: '#e0d8c8' }}>持有的前提条件：</strong>以下两点必须同时成立才维持持仓——国际收入增速维持在30%以上；销售费用率不反弹回50%以上。</p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
          {[
            { tag: '卖出考虑', color: '#f87171', bg: '#3a1a1a', text: '三诺进入微泰已有核心医保国家（德国/法国）且收入开始侵蚀' },
            { tag: '卖出考虑', color: '#f87171', bg: '#3a1a1a', text: '国际收入连续两季度增速低于25%，且无明确催化剂' },
            { tag: '观察', color: '#fbbf24', bg: '#2a2a1a', text: 'PanCares注册再次延迟超一年，无明确时间表' },
            { tag: '加仓考虑', color: '#4ade80', bg: '#1a3a2a', text: 'PanCares获批 / FDA获批 / 欧洲医保新增国家数≥10' },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13, color: '#999' }}>
              <span style={{ ...s.tag, background: item.bg, color: item.color, border: `1px solid ${item.color}33`, flexShrink: 0 }}>{item.tag}</span>
              {item.text}
            </div>
          ))}
        </div>
        <div style={{ marginTop: 14, padding: '12px 14px', background: '#1a2a3a', borderLeft: '2px solid #60a5fa', borderRadius: '0 6px 6px 0', fontSize: 13, color: '#60a5fa' }}>
          <strong>关键监控时间点：</strong>2026年Q3 NMPA审批公示（PanCares）｜2026年中报（8月）国际收入 + 销售费用率 + 欧洲医保国家数 ｜三诺2026年中报欧洲市场披露
        </div>
      </Card>

      <Card title="六、悲观情景下的安全边际测算">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}>问：如果增速从50%降到20%、三诺侵蚀一半欧洲市场份额，这13.8亿买到的生意值多少？</p>
          <p style={{ marginBottom: 10 }}>假设增速降至20%，2026年收入约7.93亿；毛利率维持52%；销售费用率反弹至45%；固定费用1.8亿。净利润约负0.5亿，接近盈亏平衡。</p>
          <p style={{ marginBottom: 10 }}>此时以3倍PS估算业务价值约23.8亿，加现金16.8亿，总值约40亿人民币。当前30.6亿市值仍有约30%隐含折价。</p>
          <p><strong style={{ color: '#e0d8c8' }}>结论：</strong>即使悲观情景成真，下行空间仍然有限，验证了安全边际逻辑。但这不是说没有风险——港股情绪波动可以在基本面不变的情况下让股价多跌30%。</p>
        </div>
      </Card>
    </>
  )
}

// ── Business Tab ──
function BusinessTab() {
  return (
    <>
      <div style={s.sectionHeader}>商业模式</div>

      <Card title="本质：剃须刀+刀片+数据平台">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}>硬件是入口，消耗品是现金流，云端数据是护城河。CGM传感器14天换一次，每个用户每年需要约26枚，形成高频、稳定、可预期的复购流。</p>
          <p>三层产品漏斗：<strong style={{ color: '#e0d8c8' }}>BGM试纸用户</strong>（高频、稳定、低客单价）→ <strong style={{ color: '#e0d8c8' }}>间歇性CGM用户</strong>（关键节点购买）→ <strong style={{ color: '#e0d8c8' }}>持续CGM+胰岛素泵用户</strong>（最高粘性，1型糖尿病患者）。APP将三层数据打通，形成患者历史档案，转换成本随时间单调递增。</p>
        </div>
      </Card>

      <Card title="三条产品线">
        <FinTable headers={['产品', '收入占比', '增速', '战略地位']}>
          <tr><Td><strong style={{ color: '#e0d8c8' }}>CGM (AiDEX X/LinX)</strong></Td><Td num>58.2%</Td><Td up>+91.5%</Td><Td>核心增长引擎，国际突破主力</Td></tr>
          <tr><Td><strong style={{ color: '#e0d8c8' }}>胰岛素泵 (Equil)</strong></Td><Td num>16.8%</Td><Td num>稳健</Td><Td>国内唯一贴敷式，差异化壁垒</Td></tr>
          <tr><Td><strong style={{ color: '#e0d8c8' }}>BGM血糖仪试纸</strong></Td><Td num>23.4%</Td><Td num>稳定</Td><Td>生态系统入口，用户留存基础</Td></tr>
          <tr style={{ background: '#1a3a2a' }}><Td><strong style={{ color: '#e0d8c8' }}>人工胰腺 (PanCares)</strong></Td><Td num>—</Td><Td num>待上市</Td><Td>2026年目标，终局战略产品</Td></tr>
        </FinTable>
      </Card>

      <Card title="三条渠道，逻辑各异">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          {[
            { label: '院内渠道', color: '#4ade80', text: '科室教育→试用→采购→检棠系统接入。一旦医院信息系统深度集成，替换成本极高。2500+家医院，B2B2C模式。' },
            { label: '欧洲医保', color: '#60a5fa', text: '政府是买家，进入报销目录=稳定批量采购，销售费用边际接近零。已进入7国，LinX国际收入+218%的核心来源。' },
            { label: '零售/电商', color: '#666', text: '非主战场，品牌曝光为主。国内零售价格战激烈（传感器已杀至73元），微泰选择不正面应战，策略是对的。' },
          ].map((ch, i) => (
            <div key={i} style={{ background: '#141414', borderRadius: 6, padding: 14 }}>
              <div style={{ fontSize: 12, fontFamily: "'Courier New', monospace", textTransform: 'uppercase', color: ch.color, marginBottom: 6 }}>{ch.label}</div>
              <div style={{ fontSize: 13, color: '#999', lineHeight: 1.8 }}>{ch.text}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="数据飞轮（最被低估的价值）">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}>20万+用户每人每天产生288条血糖读数 → 这是训练PanCares闭环算法的原材料。竞争对手需要同等规模的真实患者数据才能复制，这需要时间，不是钱能解决的。</p>
          <p><strong style={{ color: '#e0d8c8' }}>飞轮逻辑：</strong>更多用户 → 更多数据 → 更好算法 → PanCares更快获批 → 更多用户</p>
        </div>
      </Card>
    </>
  )
}

// ── Moat Tab ──
function MoatTab() {
  return (
    <>
      <div style={s.sectionHeader}>护城河分析</div>

      <Card title="四层护城河强度评估">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[
            { label: '技术壁垒', width: 50, score: '5/10', cls: 'mid', note: '3-5年，可追赶' },
            { label: '渠道锁定', width: 65, score: '6.5/10', cls: 'mid', note: '5-8年，中等' },
            { label: '欧洲医保准入', width: 72, score: '7/10', cls: 'strong', note: '2-3年缓冲期' },
            { label: '患者转换成本', width: 78, score: '8/10', cls: 'strong', note: '长期，低复制性' },
            { label: '生态系统(PanCares)', width: 30, score: '3/10', cls: 'weak', note: '仍在建设中' },
          ].map((m, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span style={{ fontSize: 13, color: '#999', minWidth: 120 }}>{m.label}</span>
              <div style={{ flex: 1, height: 6, background: '#1a1a1a', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: 3, width: `${m.width}%`,
                  background: m.cls === 'strong' ? '#4ade80' : m.cls === 'mid' ? '#fbbf24' : '#444',
                }} />
              </div>
              <span style={{ fontFamily: "'Courier New', monospace", fontSize: 12, color: '#666', minWidth: 42, textAlign: 'right' }}>{m.score}</span>
              <span style={{ fontSize: 11, color: '#555', minWidth: 110, textAlign: 'right', fontStyle: 'italic' }}>{m.note}</span>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #1e1e1e' }}>
          <div style={{ fontSize: 13, color: '#666' }}>
            <strong style={{ color: '#e0d8c8' }}>核心判断：</strong>第三层（患者转换成本）是当前真正的护城河——血糖历史数据+生理适应形成的iPhone式锁定效应。第四层（生态系统）是未来决胜点，一旦PanCares成型，转换成本将从"麻烦"变成"几乎不可能"。
          </div>
        </div>
      </Card>

      <Card title="竞争格局对比（2025H1 财务信号）">
        <FinTable headers={['指标', '微泰医疗', '三诺生物', '含义']}>
          <tr><Td>收入增速</Td><Td up>+63%</Td><Td num>+6%</Td><Td style={{ fontSize: 12, color: '#666' }}>微泰赢</Td></tr>
          <tr><Td>毛利率趋势</Td><Td up>↑51.7%</Td><Td down>↓51.9%</Td><Td style={{ fontSize: 12, color: '#666' }}>微泰质量更高</Td></tr>
          <tr><Td>销售费用率</Td><Td up>37.7%↓</Td><Td down>27%↑</Td><Td style={{ fontSize: 12, color: '#666' }}>微泰规模效应</Td></tr>
          <tr><Td>胰岛素泵</Td><Td up>有（唯一）</Td><Td down>无</Td><Td style={{ fontSize: 12, color: '#666' }}>微泰差异化</Td></tr>
          <tr><Td>国内渠道</Td><Td down>2500家</Td><Td up>3500家+</Td><Td style={{ fontSize: 12, color: '#666' }}>三诺优势</Td></tr>
          <tr><Td>欧洲医保</Td><Td up>7国</Td><Td num>评估中</Td><Td style={{ fontSize: 12, color: '#666' }}>微泰2年先发</Td></tr>
        </FinTable>
      </Card>

      <Card title="护城河最大威胁">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>短期（1-2年）：</strong>三诺已完成二代CGM欧盟CE认证（2025年7月），正在评估欧洲医保准入方案。一旦三诺进入欧洲医保，将直接竞争微泰当前最强的渠道护城河。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>中期（3-5年）：</strong>如果三诺开发出自己的贴敷式胰岛素泵（或并购），微泰"CGM+泵"的独特性将消失。目前三诺研发投入3.75亿，是微泰的5倍。</p>
          <p><strong style={{ color: '#e0d8c8' }}>需要持续观察：</strong>三诺欧洲医保进展是最值得紧盯的竞争信号，可能是2026年最重要的变量。</p>
        </div>
      </Card>
    </>
  )
}

// ── Management Tab ──
function MgmtTab() {
  return (
    <>
      <div style={s.sectionHeader}>管理层分析</div>

      <Card title="创始人：郑攀博士">
        <div style={{ display: 'grid', gridTemplateColumns: 'auto 1fr', gap: 20, alignItems: 'start' }}>
          <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#1a3a2a', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22, color: '#4ade80', flexShrink: 0 }}>郑</div>
          <div>
            <div style={{ fontSize: 15, marginBottom: 4, color: '#e0d8c8' }}>郑攀博士，董事会主席 · 执行董事 · 行政总裁</div>
            <div style={{ fontSize: 12, fontFamily: "'Courier New', monospace", color: '#666' }}>1971年生 · 浙江人 · 持股约37%</div>
            <div style={{ ...s.prose, marginTop: 10 }}>
              <p>佛罗里达州立大学机械工程博士，硅谷医疗器械从业近20年，专注微电机系统。2011年回国创立微泰，14年专注同一赛道。其在美国的前老板DORE MARK也跟随他回国加入团队——这是一个非常有力的人格信号。</p>
            </div>
          </div>
        </div>
      </Card>

      <Card title="管理层评估">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[
            { pass: true, bold: '能力匹配', text: ' — 机械+电子+生物传感器的交叉技术背景，与微泰产品高度匹配' },
            { pass: true, bold: '利益一致', text: ' — 持股37%，与外部投资者利益高度绑定，无动机做短期损害长期的事' },
            { pass: true, bold: '全球视野', text: ' — 2021年率先拿到欧盟CE认证并布局国际市场，比竞争对手早两年的战略决策' },
            { pass: true, bold: '真实执行力', text: ' — 2026年2月启动股份回购，管理层自认为股价低估的行为信号' },
            { pass: false, bold: '集权风险', text: ' — 一人身兼主席+CEO+研发负责人，多线作战能否覆盖是关键问题' },
            { pass: false, bold: 'PanCares延迟', text: ' — 比原计划晚3年，执行层面存在低估难度的历史记录' },
          ].map((item, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', fontSize: 13, color: '#999' }}>
              <span style={{ color: item.pass ? '#4ade80' : '#fbbf24' }}>{item.pass ? '✓' : '◑'}</span>
              <div><strong style={{ color: '#e0d8c8' }}>{item.bold}</strong>{item.text}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="巴菲特标准：诚信 · 才干 · 勤奋">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>诚信：</strong>股份回购行动、公益基金投入（3600万元）、信息披露相对透明，未发现重大财务造假信号。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>才干：</strong>在研发周期极长的医疗器械领域，从零到港股上市、国际市场突破，产品力获全球顶级机构背书（礼来亚洲、OrbiMed）。</p>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>勤奋：</strong>据报道无论是否周末，办公室的灯经常亮到半夜。14年只做一件事。</p>
          <p><strong style={{ color: '#e0d8c8' }}>综合评级：</strong><span style={{ ...s.tag, background: '#1a3a2a', color: '#4ade80', border: '1px solid #4ade8033' }}>B+</span> 优秀但非完美——集权结构和执行延迟是可见的不足。</p>
        </div>
      </Card>
    </>
  )
}

// ── Financials Tab ──
function FinancialsTab() {
  return (
    <>
      <div style={s.sectionHeader}>财务数据追踪</div>

      <Card title="收入与利润历史">
        <FinTable headers={['期间', '收入（亿元）', '增速', '毛利率', '销售费用率', '净利润']}>
          <tr><Td>2022年</Td><Td num>1.74</Td><Td num>—</Td><Td num>45.9%</Td><Td num>—</Td><Td down>亏损</Td></tr>
          <tr><Td>2023年</Td><Td num>2.53</Td><Td up>+45.6%</Td><Td num>47.7%</Td><Td num>—</Td><Td down>亏损</Td></tr>
          <tr><Td>2024年</Td><Td num>3.46</Td><Td up>+36.8%</Td><Td num>52.9%</Td><Td num>—</Td><Td down>-0.37亿</Td></tr>
          <tr><Td>2024H1</Td><Td num>1.51</Td><Td up>+36%</Td><Td num>47.7%</Td><Td down>66.5%</Td><Td down>-0.38亿</Td></tr>
          <tr style={{ background: '#1a3a2a' }}><Td><strong style={{ color: '#e0d8c8' }}>2025H1</strong></Td><Td num>2.46</Td><Td up>+63.1%</Td><Td up>51.7%</Td><Td up>37.7%↓</Td><Td up>-229万(↑)</Td></tr>
          <tr style={{ background: '#1a3a2a' }}><Td><strong style={{ color: '#e0d8c8' }}>2025年（全年）</strong></Td><Td num>6.61</Td><Td up>+91.2%</Td><Td up>~53%</Td><Td up>~32%</Td><Td up>+3800万+</Td></tr>
        </FinTable>
      </Card>

      <Card title="费用结构关键指标">
        <FinTable headers={['指标', '2024H1', '2025H1', '变化', '投资含义']}>
          <tr><Td>销售费用（亿元）</Td><Td num>1.00</Td><Td num>0.93</Td><Td up>↓7.4%</Td><Td style={{ fontSize: 12, color: '#666' }}>收入翻倍费用反降，结构性改善</Td></tr>
          <tr><Td>销售费用率</Td><Td down>66.5%</Td><Td up>37.7%</Td><Td up>↓28.8pp</Td><Td style={{ fontSize: 12, color: '#666' }}>欧洲医保复购无需销售费用</Td></tr>
          <tr><Td>管理费用率</Td><Td down>13.1%</Td><Td up>7.4%</Td><Td up>↓5.7pp</Td><Td style={{ fontSize: 12, color: '#666' }}>规模效应，固定成本摊薄</Td></tr>
          <tr><Td>国内收入（亿元）</Td><Td num>1.13</Td><Td num>1.25</Td><Td up>+10.6%</Td><Td style={{ fontSize: 12, color: '#666' }}>稳健增长</Td></tr>
          <tr><Td>国际收入（亿元）</Td><Td num>0.38</Td><Td up>1.21</Td><Td up>+218%</Td><Td style={{ fontSize: 12, color: '#666' }}>欧洲医保突破驱动</Td></tr>
        </FinTable>
      </Card>

      <Card title="资产负债表要点">
        <div style={s.prose}>
          <p style={{ marginBottom: 10 }}><strong style={{ color: '#e0d8c8' }}>现金储备：</strong>17.16亿人民币，无长期债务。相当于约4.0港元/股的现金价值，在当前7-8港元股价下占比超过50%。</p>
          <p><strong style={{ color: '#e0d8c8' }}>含义：</strong>扣除现金后，市场给业务本身的定价极低。即使业务发展不如预期，现金提供了相当厚的安全边际。</p>
        </div>
      </Card>
    </>
  )
}

// ── Valuation Tab ──
function ValuationTab() {
  const [baseRev, setBaseRev] = useState(6.61)
  const [shares, setShares] = useState(4.2)
  const [cashPS, setCashPS] = useState(4.0)
  const [fx, setFx] = useState(1.09)
  const [costPrice, setCostPrice] = useState(7.56)
  const [growth, setGrowth] = useState(50)
  const [ps, setPs] = useState(4.0)
  const [cashDisc, setCashDisc] = useState(0)
  const [pGm, setPGm] = useState(55)
  const [pSales, setPSales] = useState(25)
  const [pFixed, setPFixed] = useState(1.5)

  const calcPrice = useCallback((g: number, psVal: number) => {
    const rev2026 = baseRev * (1 + g / 100)
    const mktcapRmb = rev2026 * psVal
    const mktcapHkd = mktcapRmb * fx
    const bizPS = mktcapHkd / shares
    const cashAdj = cashPS * (1 - cashDisc / 100)
    return { price: (bizPS + cashAdj).toFixed(1), rev: rev2026.toFixed(2) }
  }, [baseRev, shares, cashPS, fx, cashDisc])

  const bear = calcPrice(Math.max(growth - 25, 5), Math.max(ps - 1.5, 1.5))
  const base = calcPrice(growth, ps)
  const bull = calcPrice(Math.min(growth + 20, 90), Math.min(ps + 2, 15))

  const pct = (p: string) => {
    const d = ((parseFloat(p) - costPrice) / costPrice * 100)
    return (d >= 0 ? '+' : '') + d.toFixed(0) + '%'
  }

  const varM = pGm / 100 - pSales / 100
  const revNeeded = (target: number) => ((target + pFixed) / varM).toFixed(1)
  const r3 = revNeeded(3)
  const r5 = revNeeded(5)

  const growthRates = [0, 0.50, 0.40, 0.30, 0.25, 0.20]
  const years = [2025, 2026, 2027, 2028, 2029, 2030]
  const revs: number[] = [baseRev]
  for (let i = 1; i < 6; i++) revs.push(revs[revs.length - 1] * (1 + growthRates[i]))

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '7px 10px', background: '#0a0a0a',
    border: '1px solid #2a2a2a', borderRadius: 3, color: '#e0d8c8',
    fontFamily: "'Courier New', monospace", fontSize: 13,
  }

  return (
    <>
      <div style={s.sectionHeader}>估值测算工具</div>

      <Card title="基础参数（可更新）">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14 }}>
          {[
            { label: '2025年实际收入（亿元）', value: baseRev, set: setBaseRev },
            { label: '总股本（亿股）', value: shares, set: setShares },
            { label: '现金（港元/股）', value: cashPS, set: setCashPS },
            { label: '人民币/港元汇率', value: fx, set: setFx },
            { label: '成本价（港元）', value: costPrice, set: setCostPrice },
          ].map((p, i) => (
            <div key={i}>
              <label style={{ display: 'block', ...s.metricLabel, marginBottom: 5 }}>{p.label}</label>
              <input type="number" value={p.value} step={0.01}
                onChange={e => p.set(parseFloat(e.target.value) || 0)} style={inputStyle} />
            </div>
          ))}
        </div>
      </Card>

      <Card title="调整假设">
        {[
          { label: '2026年收入增速', value: growth, set: setGrowth, min: 15, max: 80, step: 5, display: `${growth}%` },
          { label: '合理 PS 倍数（业务部分）', value: ps, set: setPs, min: 2, max: 12, step: 0.5, display: `${ps.toFixed(1)}x` },
          { label: '现金折价（0=全部计入）', value: cashDisc, set: setCashDisc, min: 0, max: 40, step: 5, display: `${cashDisc}%` },
        ].map((sl, i) => (
          <div key={i} style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 13, color: '#999' }}>{sl.label}</span>
              <span style={{ fontFamily: "'Courier New', monospace", fontSize: 13, fontWeight: 700, color: '#e0d8c8' }}>{sl.display}</span>
            </div>
            <input type="range" min={sl.min} max={sl.max} step={sl.step} value={sl.value}
              onChange={e => sl.set(parseFloat(e.target.value))} />
          </div>
        ))}
      </Card>

      <Card title="三情景价格区间">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          {[
            { label: '悲观', data: bear, g: Math.max(growth - 25, 5), p: Math.max(ps - 1.5, 1.5), bg: '#3a1a1a', border: '#991b1b33', color: '#f87171' },
            { label: '基准（你的假设）', data: base, g: growth, p: ps, bg: '#1a2a3a', border: '#1e40af33', color: '#60a5fa' },
            { label: '乐观', data: bull, g: Math.min(growth + 20, 90), p: Math.min(ps + 2, 15), bg: '#1a3a2a', border: '#16653433', color: '#4ade80' },
          ].map((sc, i) => (
            <div key={i} style={{ borderRadius: 6, padding: '14px 16px', textAlign: 'center', background: sc.bg, border: `1px solid ${sc.border}` }}>
              <div style={{ fontFamily: "'Courier New', monospace", fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6, color: sc.color }}>{sc.label}</div>
              <div style={{ fontSize: 24, letterSpacing: '-0.5px', color: '#e0d8c8' }}>HK${sc.data.price}</div>
              <div style={{ fontFamily: "'Courier New', monospace", fontSize: 12, marginTop: 3, color: sc.color }}>{pct(sc.data.price)} vs 成本</div>
              <div style={{ fontSize: 11, color: '#666', marginTop: 6, lineHeight: 1.4 }}>
                增速{sc.g}%<br />PS {sc.p.toFixed(1)}x<br />收入{sc.data.rev}亿
              </div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #1e1e1e', fontSize: 12, color: '#666', fontFamily: "'Courier New', monospace" }}>
          悲观：增速-25pp，PS-1.5x ｜ 基准：你的假设 ｜ 乐观：增速+20pp，PS+2x
        </div>
      </Card>

      <Card title="利润路径：到3-5亿净利润需要多少收入？">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14, marginBottom: 14 }}>
          {[
            { label: '成熟期毛利率', value: pGm, set: setPGm },
            { label: '销售费用率', value: pSales, set: setPSales },
            { label: '固定费用（亿/年）', value: pFixed, set: setPFixed },
          ].map((p, i) => (
            <div key={i}>
              <label style={{ display: 'block', ...s.metricLabel, marginBottom: 5 }}>{p.label}</label>
              <input type="number" value={p.value} onChange={e => p.set(parseFloat(e.target.value) || 0)} style={inputStyle} />
            </div>
          ))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div style={{ background: '#1a2a3a', border: '1px solid #1e40af22', borderRadius: 6, padding: '14px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 11, fontFamily: "'Courier New', monospace", color: '#60a5fa', textTransform: 'uppercase', marginBottom: 6 }}>达到净利润 3亿</div>
            <div style={{ fontSize: 24, color: '#e0d8c8' }}>{r3}<span style={{ fontSize: 14 }}>亿收入</span></div>
            <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>利润率约 {(3 / parseFloat(r3) * 100).toFixed(1)}%</div>
          </div>
          <div style={{ background: '#1a3a2a', border: '1px solid #16653422', borderRadius: 6, padding: '14px 16px', textAlign: 'center' }}>
            <div style={{ fontSize: 11, fontFamily: "'Courier New', monospace", color: '#4ade80', textTransform: 'uppercase', marginBottom: 6 }}>达到净利润 5亿</div>
            <div style={{ fontSize: 24, color: '#e0d8c8' }}>{r5}<span style={{ fontSize: 14 }}>亿收入</span></div>
            <div style={{ fontSize: 11, color: '#666', marginTop: 4 }}>利润率约 {(5 / parseFloat(r5) * 100).toFixed(1)}%</div>
          </div>
        </div>

        <div style={{ marginTop: 16, fontSize: 12, color: '#666', fontFamily: "'Courier New', monospace", marginBottom: 8 }}>
          增速假设：2026→50%，2027→40%，2028→30%，2029→25%，2030→20%
        </div>
        <FinTable headers={['年份', '收入（亿）', '净利润（亿）', '里程碑']}>
          {years.map((y, i) => {
            const rev = revs[i]
            const profit = rev * varM - pFixed
            const isHighlight = (profit >= 3 && (i === 0 || revs[i - 1] * varM - pFixed < 3)) || (profit >= 5 && (i === 0 || revs[i - 1] * varM - pFixed < 5))
            return (
              <tr key={y} style={isHighlight ? { background: '#1a3a2a' } : {}}>
                <Td>{y}</Td>
                <Td num>{rev.toFixed(2)}</Td>
                <Td up={profit >= 0} down={profit < 0}>{profit >= 0 ? '+' : ''}{profit.toFixed(2)}</Td>
                <Td>
                  {profit >= 5 && (i === 0 || revs[i - 1] * varM - pFixed < 5) && <span style={{ ...s.tag, background: '#1a3a2a', color: '#4ade80' }}>5亿</span>}
                  {profit >= 3 && profit < 5 && (i === 0 || revs[i - 1] * varM - pFixed < 3) && <span style={{ ...s.tag, background: '#1a2a3a', color: '#60a5fa' }}>3亿</span>}
                </Td>
              </tr>
            )
          })}
        </FinTable>
      </Card>

      <Card title="同类可比公司 PS 参考">
        <FinTable headers={['公司', '当前/历史PS', '备注']}>
          <tr><Td><strong style={{ color: '#e0d8c8' }}>微泰医疗（现在）</strong></Td><Td up>~4x</Td><Td>扣现金后约2x</Td></tr>
          <tr><Td>德康 Dexcom</Td><Td num>历史 8-15x</Td><Td>全球CGM龙头，美国市场</Td></tr>
          <tr><Td>Insulet（贴敷泵）</Td><Td num>历史 8-12x</Td><Td>OmniPod贴敷式泵</Td></tr>
          <tr><Td>雅培 Abbott</Td><Td num>历史 4-6x</Td><Td>多元化医疗巨头</Td></tr>
          <tr><Td>港股医疗器械均值</Td><Td num>3-5x</Td><Td>市场整体折价</Td></tr>
          <tr><Td>三诺生物（A股）</Td><Td num>~5-6x PE</Td><Td>成熟盈利公司</Td></tr>
        </FinTable>
        <div style={{ marginTop: 10, fontSize: 12, color: '#666', fontStyle: 'italic' }}>华创证券目标价：13.7港元（强推），中信建投：买入</div>
      </Card>
    </>
  )
}

// ── Watchlist Tab ──
function WatchlistTab() {
  const watchItems = [
    { priority: 'red', title: '三诺欧洲医保准入进展', desc: '三诺2025年7月二代CGM获欧盟CE认证，正评估医保准入方案。一旦进入与微泰竞争的国家，是微泰国际护城河被侵蚀的最直接信号。', timing: '紧迫性：极高 · 需每季度跟踪 · 2026年全年关注' },
    { priority: 'red', title: 'PanCares人工胰腺：NMPA注册进度', desc: '2025年已提交注册申请，预计2026年获批上市。是微泰护城河第四层的关键催化剂，一旦获批将大幅提升估值锚点。', timing: '紧迫性：极高 · 2026年Q1-Q2关键窗口期' },
    { priority: 'red', title: 'FDA 510(k) 审批结果', desc: '目前在实质性审查阶段，是进入美国市场（全球CGM市占45%）的门票，也是股价最大的期权。获批=收入规模可能翻倍的新叙事。', timing: '紧迫性：高 · 2026年内有望有结果' },
    { priority: 'amber', title: '欧洲医保覆盖国家数量', desc: '从7国扩展到10国+是收入增速持续的结构性支撑。每新增1个医保国家 = 稳定批量采购，无需额外销售费用。跟踪半年报披露数字。', timing: '频率：每半年（中报/年报）' },
    { priority: 'amber', title: '销售费用率是否继续下降', desc: '2025H1已从66.5%降至37.7%。这个趋势能否持续是整个利润模型的核心假设。目标：2026年全年降至30%以下。', timing: '频率：每季度估算，半年报确认' },
    { priority: 'amber', title: 'Equil胰岛素泵第二代上市进度', desc: '已向NMPA提交注册，具有更高防水等级和更大储药器。第二代产品是保持泵业务增长的关键，也是PanCares的硬件基础。', timing: '频率：每季度公告' },
    { priority: 'green', title: '国内入院数量：2500→3500+', desc: '缩短与三诺（3500家）的差距是国内竞争力的直接体现。每半年跟踪入院数字，目标2027年达到3000+家。', timing: '频率：每半年（中报/年报）' },
    { priority: 'green', title: '毛利率能否突破55%', desc: '从现在的52%到55%是利润模型的分水岭。规模扩大+良品率提升+产品结构优化（CGM占比提升）三力合一才能实现。', timing: '频率：每半年（中报/年报）' },
  ]

  const dotColor: Record<string, string> = { red: '#f87171', amber: '#fbbf24', green: '#4ade80' }

  return (
    <>
      <div style={s.sectionHeader}>持续关注指标</div>

      <Card title="催化剂 · 按紧迫程度排序">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {watchItems.map((w, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: '12px 14px', borderRadius: 6, border: '1px solid #1e1e1e', background: '#0f0f0f' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', flexShrink: 0, marginTop: 6, background: dotColor[w.priority] }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, color: '#e0d8c8', fontWeight: 700, marginBottom: 2 }}>{w.title}</div>
                <div style={{ fontSize: 12, color: '#666', lineHeight: 1.5 }}>{w.desc}</div>
                <div style={{ fontFamily: "'Courier New', monospace", fontSize: 10, color: '#444', marginTop: 3 }}>{w.timing}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="数字追踪板（更新记录）">
        <FinTable headers={['指标', '上一期', '最新', '趋势', '下次更新']}>
          <tr><Td>国际收入（亿）</Td><Td num>0.38</Td><Td up>1.21</Td><Td up>+218%</Td><Td style={{ fontSize: 12 }}>2026年中报</Td></tr>
          <tr><Td>欧洲医保国家</Td><Td num>~5</Td><Td up>7</Td><Td up>↑</Td><Td style={{ fontSize: 12 }}>2026年中报</Td></tr>
          <tr><Td>国内入院数</Td><Td num>2000+</Td><Td num>2500+</Td><Td up>↑</Td><Td style={{ fontSize: 12 }}>2026年中报</Td></tr>
          <tr><Td>销售费用率</Td><Td down>66.5%</Td><Td up>37.7%</Td><Td up>↓大幅</Td><Td style={{ fontSize: 12 }}>2025年报</Td></tr>
          <tr><Td>毛利率</Td><Td num>47.7%</Td><Td up>51.7%</Td><Td up>↑</Td><Td style={{ fontSize: 12 }}>2025年报</Td></tr>
          <tr><Td>年净利润</Td><Td down>亏损</Td><Td up>+3800万</Td><Td up>首次盈利</Td><Td style={{ fontSize: 12 }}>2025年报</Td></tr>
        </FinTable>
      </Card>
    </>
  )
}

// ── Log Tab ──
interface LogEntry { d: string; type: string; title: string; content: string }

function LogTab() {
  const [logs, setLogs] = useState<LogEntry[]>(() => {
    try { return JSON.parse(localStorage.getItem('microtech-logs') || '[]') } catch { return [] }
  })
  const [showModal, setShowModal] = useState(false)
  const [newLog, setNewLog] = useState({ d: new Date().toISOString().slice(0, 10), type: 'positive', title: '', content: '' })

  const saveLog = () => {
    if (!newLog.content.trim()) return
    const updated = [newLog, ...logs]
    setLogs(updated)
    localStorage.setItem('microtech-logs', JSON.stringify(updated))
    setShowModal(false)
    setNewLog({ d: new Date().toISOString().slice(0, 10), type: 'positive', title: '', content: '' })
  }

  const deleteLog = (i: number) => {
    const updated = logs.filter((_, idx) => idx !== i)
    setLogs(updated)
    localStorage.setItem('microtech-logs', JSON.stringify(updated))
  }

  const borderColors: Record<string, string> = { positive: '#4ade80', negative: '#f87171', neutral: '#fbbf24' }

  const builtInLogs = [
    { d: '2026-04', type: 'positive', title: '投资备忘录完成', content: '完成深度分析并整理正式投资备忘录。核心结论：30.6亿市值中16.8亿是现金，扣除后13.8亿买下年收入6.61亿的全球化生意，EV/收入约2倍，安全边际充分。PanCares 2026年下半年预计获批，为赠送期权而非押注前提。' },
    { d: '2026-04', type: 'negative', title: '三诺欧洲进展核实', content: '经核实，三诺威胁比之前估计的更具体：已进入英国、奥地利国家医保目录，在瑞典、西班牙、意大利有招标中标，借助Menarini独家经销商布局欧洲20+国医保市场。这是真实发生的竞争，不是潜在威胁。微泰仍有7国先发优势，但2026年竞争格局会实质改变。需每季度跟踪三诺欧洲收入披露。' },
    { d: '2026-02', type: 'positive', title: '2025年报业绩', content: '2025年全年收入6.608亿（+91.2%），净利润首次转正3800万+。销售费用率降至约32%，规模效应验证。重要里程碑：商业模式可行性得到第一次真实验证。' },
    { d: '2025-09', type: 'positive', title: '市场进展', content: '郑攀出席京东JDD大会，披露产品已进入7个欧洲国家医保体系。PanCares闭环人工胰腺预计2026年推出。Equil胰岛素泵扩展至3-17岁儿童青少年适应症。' },
    { d: '2025-08', type: 'positive', title: '中期业绩', content: '2025H1收入2.46亿(+63.1%)，国际收入1.21亿(+218%)，净亏损仅229万（较上年3773万大幅收窄93.9%）。销售费用率从66.5%骤降至37.7%——绝对值反而减少7.4%。这是财务质量改善最清晰的信号。' },
    { d: '2025-07', type: 'neutral', title: '竞争动态', content: '三诺生物二代CGM获欧盟CE-MDR认证，正评估医保准入方案。这是微泰最大竞争风险的具体化。需持续跟踪三诺欧洲商业化进度，预计2026年起见竞争影响。' },
    { d: '2025-04', type: 'neutral', title: '建仓记录', content: '以7.561港元均价买入100股（Tiger Securities），总成本约756港元。这是Plan A第一笔仓位，属于探索性持仓，规模与风险认知匹配。成本约7.56港元。' },
  ]

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '9px 12px', background: '#0a0a0a',
    border: '1px solid #2a2a2a', borderRadius: 3, color: '#e0d8c8',
    fontFamily: 'Georgia, serif', fontSize: 14,
  }

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={s.sectionHeader}>研究日志</div>
        <button onClick={() => setShowModal(true)} style={{
          background: 'none', border: '1px solid #2a2a2a', color: '#999',
          padding: '8px 16px', borderRadius: 6, cursor: 'pointer',
          fontFamily: 'Georgia, serif', fontSize: 13,
        }}>+ 添加记录</button>
      </div>

      {showModal && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
          onClick={e => { if (e.target === e.currentTarget) setShowModal(false) }}>
          <div style={{ background: '#141414', borderRadius: 6, padding: 28, width: 420, maxWidth: '95vw', border: '1px solid #2a2a2a' }}>
            <div style={{ fontSize: 16, marginBottom: 18, color: '#e0d8c8' }}>添加研究记录</div>
            <div style={{ display: 'flex', gap: 10, marginBottom: 14 }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', ...s.metricLabel, marginBottom: 5 }}>日期</label>
                <input type="date" value={newLog.d} onChange={e => setNewLog({ ...newLog, d: e.target.value })} style={inputStyle} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', ...s.metricLabel, marginBottom: 5 }}>类型</label>
                <select value={newLog.type} onChange={e => setNewLog({ ...newLog, type: e.target.value })} style={inputStyle}>
                  <option value="positive">正面进展</option>
                  <option value="negative">负面风险</option>
                  <option value="neutral">中性信息</option>
                </select>
              </div>
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', ...s.metricLabel, marginBottom: 5 }}>标题/来源（选填）</label>
              <input value={newLog.title} onChange={e => setNewLog({ ...newLog, title: e.target.value })} placeholder="如：2026年中报 · 竞争动态" style={inputStyle} />
            </div>
            <div style={{ marginBottom: 14 }}>
              <label style={{ display: 'block', ...s.metricLabel, marginBottom: 5 }}>内容</label>
              <textarea value={newLog.content} onChange={e => setNewLog({ ...newLog, content: e.target.value })}
                placeholder="记录关键数据、判断变化、市场进展..." style={{ ...inputStyle, minHeight: 80, resize: 'vertical' }} />
            </div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowModal(false)} style={{ background: 'none', border: '1px solid #2a2a2a', color: '#999', padding: '9px 16px', borderRadius: 3, cursor: 'pointer', fontFamily: 'Georgia, serif', fontSize: 14 }}>取消</button>
              <button onClick={saveLog} style={{ background: '#4ade80', color: '#0a0a0a', border: 'none', padding: '9px 20px', borderRadius: 3, cursor: 'pointer', fontFamily: 'Georgia, serif', fontSize: 14 }}>保存</button>
            </div>
          </div>
        </div>
      )}

      <Card title="进展记录">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* User-added logs */}
          {logs.map((l, i) => (
            <div key={`user-${i}`} style={{ borderLeft: `2px solid ${borderColors[l.type] || '#fbbf24'}`, padding: '4px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: "'Courier New', monospace", fontSize: 11, color: '#666', marginBottom: 3 }}>
                <span>{l.d.slice(0, 7)} · {l.title || '更新'}</span>
                <button onClick={() => deleteLog(i)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#444', fontSize: 13, padding: '2px 4px' }}>✕</button>
              </div>
              <div style={{ fontSize: 13, color: '#999', lineHeight: 1.6 }}>{l.content}</div>
            </div>
          ))}
          {/* Built-in logs */}
          {builtInLogs.map((l, i) => (
            <div key={`builtin-${i}`} style={{ borderLeft: `2px solid ${borderColors[l.type] || '#fbbf24'}`, padding: '4px 16px' }}>
              <div style={{ fontFamily: "'Courier New', monospace", fontSize: 11, color: '#666', marginBottom: 3 }}>
                {l.d} · {l.title}
              </div>
              <div style={{ fontSize: 13, color: '#999', lineHeight: 1.6 }}>{l.content}</div>
            </div>
          ))}
        </div>
      </Card>
    </>
  )
}

// ── Main Holdings Component ──
export default function Holdings() {
  const [activeTab, setActiveTab] = useState<HoldingsTab>('overview')

  const tabContent: Record<HoldingsTab, React.ReactNode> = {
    overview: <OverviewTab />,
    memo: <MemoTab />,
    business: <BusinessTab />,
    moat: <MoatTab />,
    mgmt: <MgmtTab />,
    financials: <FinancialsTab />,
    valuation: <ValuationTab />,
    watchlist: <WatchlistTab />,
    log: <LogTab />,
  }

  return (
    <div>
      {/* Header */}
      <div style={{ background: '#080808', padding: '20px 24px 16px', borderBottom: '1px solid #181818' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ fontFamily: "'Courier New', monospace", fontSize: 11, letterSpacing: '0.12em', color: '#4ade80', textTransform: 'uppercase', marginBottom: 4 }}>
              HK:2235 · 港股 · 医疗器械
            </div>
            <div style={{ fontSize: 20, fontWeight: 400, letterSpacing: '-0.3px', color: '#e0d8c8' }}>
              微泰医疗器械（杭州）
            </div>
          </div>
          <div style={{ background: '#1a3a2a', color: '#4ade80', padding: '6px 14px', borderRadius: 3, fontFamily: "'Courier New', monospace", fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
            持有观察
          </div>
        </div>
        <div style={{ display: 'flex', gap: 20, marginTop: 14, flexWrap: 'wrap' }}>
          {[
            { label: '成本价', value: 'HK$7.56' },
            { label: '当前价（2026.04）', value: 'HK$7.90', up: true },
            { label: '总市值', value: '~30.6亿人民币' },
            { label: '持仓', value: '100股' },
            { label: '2025年收入', value: '6.61亿↑91%', up: true },
            { label: '首次盈利', value: '3800万+', up: true },
            { label: '更新日期', value: '2026.04.21' },
          ].map((m, i) => (
            <div key={i} style={{ fontFamily: "'Courier New', monospace", fontSize: 12 }}>
              <span style={{ display: 'block', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.1em', color: '#666', marginBottom: 1 }}>{m.label}</span>
              <span style={{ color: m.up ? '#4ade80' : '#e0d8c8' }}>{m.value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Tab nav */}
      <div style={{ background: '#080808', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', gap: 0, overflowX: 'auto' }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: activeTab === tab.id ? '#4ade80' : '#666',
              padding: '10px 18px',
              fontFamily: "'Courier New', monospace", fontSize: 11,
              letterSpacing: '0.08em', textTransform: 'uppercase',
              whiteSpace: 'nowrap',
              borderBottom: activeTab === tab.id ? '2px solid #4ade80' : '2px solid transparent',
              transition: 'all 0.15s',
            }}
          >{tab.label}</button>
        ))}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '32px 20px 80px' }}>
        {tabContent[activeTab]}
      </div>
    </div>
  )
}
