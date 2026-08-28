import { useEffect, useMemo, useState } from 'react'
import styles from './ModelSettings.module.css'

type Capability = 'generation' | 'embedding' | 'reranker'

interface ModelConfig {
  id: string
  capability: Capability
  enabled: boolean
  dimension?: number | null
}

interface ProviderConfig {
  id: string
  name: string
  provider: 'openai_compatible' | 'openai' | 'anthropic' | 'gemini'
  base_url: string
  api_key?: string
  has_api_key?: boolean
  clear_api_key?: boolean
  models: ModelConfig[]
}

interface AISettings {
  version?: number
  providers: ProviderConfig[]
  routes: Record<string, string>
  vector_collection: string
  saved?: boolean
}

const TASKS = [
  ['knowledge_answer', '知识库回答'],
  ['tutor_dialogue', '思维训练营'],
  ['coach_dialogue', '投资教练'],
  ['structured_feedback', '结构化反馈'],
  ['long_synthesis', '长篇综合'],
  ['daily_digest', '每日简报'],
] as const

const CAPABILITY_LABEL: Record<Capability, string> = {
  generation: '对话 / 生成',
  embedding: '向量化',
  reranker: '重排',
}

function endpoint(path: string) {
  const base = localStorage.getItem('digest-backend-url') || ''
  return base ? `${base.replace(/\/$/, '')}${path}` : path
}

function profileId(providerId: string, modelId: string) {
  return `${providerId}::${modelId}`
}

function errorText(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

export default function ModelSettings() {
  const [settings, setSettings] = useState<AISettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [notice, setNotice] = useState<{ type: 'ok' | 'error' | 'warning'; text: string } | null>(null)
  const [testing, setTesting] = useState('')
  const [testResults, setTestResults] = useState<Record<string, string>>({})

  useEffect(() => {
    fetch(endpoint('/api/ai/settings'))
      .then(async response => {
        const body = await response.json()
        if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`)
        setSettings(body)
      })
      .catch(error => setNotice({ type: 'error', text: `加载模型配置失败：${errorText(error)}` }))
      .finally(() => setLoading(false))
  }, [])

  const modelOptions = useMemo(() => {
    const result: Record<Capability, { value: string; label: string }[]> = {
      generation: [], embedding: [], reranker: [],
    }
    settings?.providers.forEach(provider => provider.models.forEach(model => {
      if (model.enabled && model.id.trim()) {
        result[model.capability].push({
          value: profileId(provider.id, model.id),
          label: `${provider.name} · ${model.id}`,
        })
      }
    }))
    return result
  }, [settings])

  function updateProvider(index: number, patch: Partial<ProviderConfig>) {
    setSettings(current => current && ({
      ...current,
      providers: current.providers.map((provider, i) => i === index ? { ...provider, ...patch } : provider),
    }))
  }

  function updateModel(providerIndex: number, modelIndex: number, patch: Partial<ModelConfig>) {
    setSettings(current => {
      if (!current) return current
      const provider = current.providers[providerIndex]
      const oldModel = provider.models[modelIndex]
      const updated = { ...oldModel, ...patch }
      const oldProfile = profileId(provider.id, oldModel.id)
      const newProfile = profileId(provider.id, updated.id)
      return {
        ...current,
        routes: Object.fromEntries(Object.entries(current.routes).map(([key, value]) => [
          key, value === oldProfile ? newProfile : value,
        ])),
        providers: current.providers.map((item, i) => i === providerIndex ? {
          ...item,
          models: item.models.map((model, j) => j === modelIndex ? updated : model),
        } : item),
      }
    })
  }

  function removeModel(providerIndex: number, modelIndex: number) {
    setSettings(current => {
      if (!current) return current
      const provider = current.providers[providerIndex]
      const removed = profileId(provider.id, provider.models[modelIndex].id)
      return {
        ...current,
        routes: Object.fromEntries(Object.entries(current.routes).map(([key, value]) => [key, value === removed ? '' : value])),
        providers: current.providers.map((item, i) => i === providerIndex ? {
          ...item, models: item.models.filter((_, j) => j !== modelIndex),
        } : item),
      }
    })
  }

  function addProvider() {
    if (!settings) return
    const number = settings.providers.length + 1
    setSettings({
      ...settings,
      providers: [...settings.providers, {
        id: `provider-${number}`,
        name: `供应商 ${number}`,
        provider: 'openai_compatible',
        base_url: '',
        models: [{ id: '', capability: 'generation', enabled: true }],
      }],
    })
  }

  async function save() {
    if (!settings) return
    setSaving(true)
    setNotice(null)
    try {
      const response = await fetch(endpoint('/api/ai/settings'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          providers: settings.providers,
          routes: settings.routes,
          vector_collection: settings.vector_collection,
        }),
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`)
      setSettings(body.settings)
      setNotice({
        type: body.reindex_required ? 'warning' : 'ok',
        text: body.reindex_required
          ? '配置已保存。向量模型发生变化，使用知识库前请用新模型重新构建向量索引。'
          : '配置已保存，新的模型路由已立即生效。',
      })
    } catch (error) {
      setNotice({ type: 'error', text: `保存失败：${errorText(error)}` })
    } finally {
      setSaving(false)
    }
  }

  async function testModel(provider: ProviderConfig, model: ModelConfig, providerIndex: number, modelIndex: number) {
    const key = profileId(provider.id, model.id)
    setTesting(key)
    setTestResults(current => ({ ...current, [key]: '正在连接…' }))
    try {
      const response = await fetch(endpoint('/api/ai/test'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: provider.id,
          provider: provider.provider,
          base_url: provider.base_url,
          api_key: provider.api_key || '',
          model: model.id,
          capability: model.capability,
        }),
      })
      const body = await response.json()
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`)
      const dimension = body.dimension ? `，维度 ${body.dimension}` : ''
      if (model.capability === 'embedding' && body.dimension) {
        updateModel(providerIndex, modelIndex, { dimension: body.dimension })
      }
      setTestResults(current => ({ ...current, [key]: `✓ ${body.detail}${dimension}，${body.latency_ms}ms` }))
    } catch (error) {
      setTestResults(current => ({ ...current, [key]: `✕ ${errorText(error)}` }))
    } finally {
      setTesting('')
    }
  }

  if (loading) return <div className={styles.loading}>正在加载模型配置…</div>
  if (!settings) return <div className={styles.loading}>模型配置不可用，请确认后端已启动。</div>

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div>
          <div className={styles.eyebrow}>AI GATEWAY</div>
          <h1>模型设置</h1>
          <p>在页面中管理第三方生成、向量化和重排模型。API Key 只提交给本机后端，不保存在浏览器。</p>
        </div>
        <button className={styles.saveButton} onClick={save} disabled={saving}>
          {saving ? '保存中…' : '保存并应用'}
        </button>
      </header>

      {notice && <div className={`${styles.notice} ${styles[notice.type]}`}>{notice.text}</div>}

      <section className={styles.securityNote}>
        <strong>密钥保护</strong>
        <span>后端仅返回“是否已保存”，不会把完整 Key 发回页面。Key 输入框留空时会保留原值。</span>
      </section>

      {settings.providers.map((provider, providerIndex) => (
        <section className={styles.providerCard} key={`${provider.id}-${providerIndex}`}>
          <div className={styles.cardTitle}>
            <div>
              <span className={styles.providerNumber}>供应商 {providerIndex + 1}</span>
              <h2>{provider.name || '未命名供应商'}</h2>
            </div>
            {settings.providers.length > 1 && (
              <button className={styles.dangerButton} onClick={() => setSettings({
                ...settings, providers: settings.providers.filter((_, i) => i !== providerIndex),
              })}>删除供应商</button>
            )}
          </div>

          <div className={styles.providerGrid}>
            <label>
              <span>显示名称</span>
              <input value={provider.name} onChange={e => updateProvider(providerIndex, { name: e.target.value })} />
            </label>
            <label>
              <span>接口类型</span>
              <select value={provider.provider} onChange={e => updateProvider(providerIndex, { provider: e.target.value as ProviderConfig['provider'] })}>
                <option value="openai_compatible">OpenAI 兼容</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="gemini">Gemini OpenAI 兼容</option>
              </select>
            </label>
            <label className={styles.wideField}>
              <span>API Base URL</span>
              <input value={provider.base_url} placeholder="https://api.example.com/v1" onChange={e => updateProvider(providerIndex, { base_url: e.target.value })} />
            </label>
            <label className={styles.wideField}>
              <span>API Key {provider.has_api_key && <em>（已安全保存）</em>}</span>
              <input
                type="password"
                autoComplete="new-password"
                value={provider.api_key || ''}
                placeholder={provider.has_api_key ? '留空则保留已保存的 Key' : '请手动填写 Key'}
                onChange={e => updateProvider(providerIndex, { api_key: e.target.value, clear_api_key: false })}
              />
            </label>
          </div>

          <div className={styles.modelsHeader}>
            <div>
              <h3>模型列表</h3>
              <p>模型名称需与供应商后台显示的 ID 完全一致。</p>
            </div>
            <button className={styles.secondaryButton} onClick={() => updateProvider(providerIndex, {
              models: [...provider.models, { id: '', capability: 'generation', enabled: true }],
            })}>＋ 新增模型</button>
          </div>

          <div className={styles.modelTable}>
            <div className={styles.modelTableHeader}>
              <span>模型 ID</span><span>能力</span><span>向量维度</span><span>状态与测试</span><span />
            </div>
            {provider.models.map((model, modelIndex) => {
              const testKey = profileId(provider.id, model.id)
              return (
                <div className={styles.modelRow} key={`${testKey}-${modelIndex}`}>
                  <input value={model.id} placeholder="model-name" onChange={e => updateModel(providerIndex, modelIndex, { id: e.target.value })} />
                  <select value={model.capability} onChange={e => updateModel(providerIndex, modelIndex, { capability: e.target.value as Capability })}>
                    {Object.entries(CAPABILITY_LABEL).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
                  </select>
                  <input
                    type="number"
                    min="1"
                    disabled={model.capability !== 'embedding'}
                    value={model.dimension ?? ''}
                    placeholder="自动检测"
                    onChange={e => updateModel(providerIndex, modelIndex, { dimension: e.target.value ? Number(e.target.value) : null })}
                  />
                  <div className={styles.testCell}>
                    <label className={styles.toggle}><input type="checkbox" checked={model.enabled} onChange={e => updateModel(providerIndex, modelIndex, { enabled: e.target.checked })} />启用</label>
                    <button disabled={!model.id.trim() || testing === testKey} onClick={() => testModel(provider, model, providerIndex, modelIndex)}>
                      {testing === testKey ? '测试中' : '测试'}
                    </button>
                    {testResults[testKey] && <small className={testResults[testKey].startsWith('✓') ? styles.testOk : styles.testError}>{testResults[testKey]}</small>}
                  </div>
                  <button className={styles.iconButton} onClick={() => removeModel(providerIndex, modelIndex)} title="删除模型">×</button>
                </div>
              )
            })}
          </div>
        </section>
      ))}

      <button className={styles.addProvider} onClick={addProvider}>＋ 新增供应商</button>

      <section className={styles.routesCard}>
        <div className={styles.cardTitle}>
          <div><span className={styles.providerNumber}>ROUTING</span><h2>任务路由</h2></div>
        </div>
        <div className={styles.routesGrid}>
          <label>
            <span>向量集合名</span>
            <input
              value={settings.vector_collection || ''}
              onChange={e => setSettings({ ...settings, vector_collection: e.target.value })}
              placeholder="buffett_kb_provider_model_v1"
            />
          </label>
          <div className={styles.routeSpacer} />
          {TASKS.map(([task, label]) => (
            <label key={task}>
              <span>{label}</span>
              <select value={settings.routes[task] || ''} onChange={e => setSettings({ ...settings, routes: { ...settings.routes, [task]: e.target.value } })}>
                <option value="">请选择生成模型</option>
                {modelOptions.generation.map(option => <option value={option.value} key={option.value}>{option.label}</option>)}
              </select>
            </label>
          ))}
          <label>
            <span>知识库向量化</span>
            <select value={settings.routes.embedding || ''} onChange={e => setSettings({ ...settings, routes: { ...settings.routes, embedding: e.target.value } })}>
              <option value="">请选择向量模型</option>
              {modelOptions.embedding.map(option => <option value={option.value} key={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label>
            <span>检索结果重排（可选）</span>
            <select value={settings.routes.reranker || ''} onChange={e => setSettings({ ...settings, routes: { ...settings.routes, reranker: e.target.value } })}>
              <option value="">不启用重排</option>
              {modelOptions.reranker.map(option => <option value={option.value} key={option.value}>{option.label}</option>)}
            </select>
          </label>
        </div>
        <p className={styles.reindexNote}>更换向量模型后，已有向量索引不能直接复用，需要用新模型重新导入知识库；页面不会自动执行这个高成本操作。</p>
      </section>
    </div>
  )
}
