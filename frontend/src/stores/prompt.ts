import { defineStore } from 'pinia'

export interface HistoryItem { id: number; topic: string; output: string; date: string; style: string }
export interface ModelProvider { id: string; name: string; base_url: string; model: string }

export const usePromptStore = defineStore('prompt', {
  state: () => ({
    topic: '', context: '', audience: '', style: 'balanced', includeVariables: true,
    output: '', isStreaming: false, error: '', backendMode: 'demo', theme: 'paper',
    history: [] as HistoryItem[],
    providers: [] as ModelProvider[],
    modelProvider: 'openai', modelBaseUrl: 'https://api.openai.com/v1',
    modelName: 'gpt-4o-mini', modelApiKey: '',
    modelTestState: 'idle' as 'idle' | 'testing' | 'success' | 'error', modelTestMessage: '',
  }),
  actions: {
    async generate() {
      if (!this.topic.trim() || this.isStreaming) return
      this.output = ''
      this.error = ''
      this.isStreaming = true
      try {
        const response = await fetch('/api/generate/stream', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            topic: this.topic, context: this.context, audience: this.audience,
            style: this.style, include_variables: this.includeVariables,
            ...(this.modelApiKey ? {
              provider: this.modelProvider, base_url: this.modelBaseUrl,
              model: this.modelName, api_key: this.modelApiKey,
            } : {}),
          }),
        })
        if (!response.ok || !response.body) throw new Error('暂时无法连接生成服务，请确认后端已经启动。')
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { value, done } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const events = buffer.split('\n\n')
          buffer = events.pop() || ''
          for (const event of events) {
            const line = event.split('\n').find((entry) => entry.startsWith('data: '))
            if (!line) continue
            const payload = JSON.parse(line.slice(6))
            if (payload.type === 'chunk') this.output += payload.content
            if (payload.type === 'meta') this.backendMode = payload.mode
            if (payload.type === 'error') throw new Error(payload.message)
          }
        }
        if (this.output) this.history.unshift({ id: Date.now(), topic: this.topic, output: this.output, date: new Date().toLocaleString('zh-CN'), style: this.style })
      } catch (error) {
        this.error = error instanceof Error ? error.message : '生成失败，请稍后重试。'
      } finally {
        this.isStreaming = false
      }
    },
    async loadProviders() {
      try {
        const response = await fetch('/api/providers')
        if (!response.ok) throw new Error('无法加载服务商列表')
        const data = await response.json()
        this.providers = data.providers
        const selected = this.providers.find((provider) => provider.id === this.modelProvider)
        if (selected) {
          this.modelBaseUrl = selected.base_url
          this.modelName = selected.model
        }
      } catch {
        this.modelTestMessage = '服务商列表暂时不可用，请检查后端服务。'
      }
    },
    chooseProvider(providerId: string) {
      this.modelProvider = providerId
      const selected = this.providers.find((provider) => provider.id === providerId)
      if (selected) {
        this.modelBaseUrl = selected.base_url
        this.modelName = selected.model
      }
      this.modelTestState = 'idle'
      this.modelTestMessage = ''
    },
    async testModel() {
      if (!this.modelApiKey.trim() || !this.modelBaseUrl.trim() || !this.modelName.trim()) {
        this.modelTestState = 'error'
        this.modelTestMessage = '请填写 API Key、接口地址和模型名称。'
        return
      }
      this.modelTestState = 'testing'
      this.modelTestMessage = '正在发送一条简短测试请求…'
      try {
        const response = await fetch('/api/models/test', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ provider: this.modelProvider, base_url: this.modelBaseUrl, model: this.modelName, api_key: this.modelApiKey }),
        })
        const result = await response.json()
        this.modelTestState = result.ok ? 'success' : 'error'
        this.modelTestMessage = result.message || (result.ok ? '连接成功。' : '连接失败。')
      } catch {
        this.modelTestState = 'error'
        this.modelTestMessage = '无法连接本地后端，请确认服务正在运行。'
      }
    },
    clearModelKey() {
      this.modelApiKey = ''
      this.modelTestState = 'idle'
      this.modelTestMessage = '已从当前页面会话中清除 API Key。'
    },
    loadHistory(item: HistoryItem) { this.topic = item.topic; this.output = item.output },
    reset() { this.topic = ''; this.context = ''; this.audience = ''; this.output = ''; this.error = '' },
  },
})
