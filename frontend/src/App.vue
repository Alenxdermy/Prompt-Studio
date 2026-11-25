<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { usePromptStore } from './stores/prompt'
import {
  ArrowDown, ArrowRight, Check, ChevronDown, CircleAlert, CircleCheck, Clipboard, Copy,
  Eye, EyeOff, FilePlus2, History, KeyRound, Lightbulb, LoaderCircle, Palette,
  RotateCcw, ShieldCheck, Sparkles, WandSparkles,
} from 'lucide-vue-next'

const store = usePromptStore()
const activeTab = ref('compose')
const showThemes = ref(false)
const copied = ref(false)
const revealKey = ref(false)
const themes = [
  { id: 'paper', name: '暖纸', color: '#f4e6b8', ink: '#173242' },
  { id: 'mint', name: '薄荷', color: '#dcebe1', ink: '#19483d' },
  { id: 'sky', name: '晴空', color: '#dce9f0', ink: '#173a4d' },
  { id: 'rose', name: '浅樱', color: '#f1dfe0', ink: '#52353a' },
]
const outputReady = computed(() => store.output.length > 0)
const wordCount = computed(() => store.output.trim().split(/\s+/).filter(Boolean).length)

onMounted(() => {
  const saved = localStorage.getItem('prompt-studio-theme') || 'paper'
  document.documentElement.dataset.theme = saved
  store.theme = saved
  void store.loadProviders()
})

function setTheme(id: string) {
  document.documentElement.dataset.theme = id
  store.theme = id
  localStorage.setItem('prompt-studio-theme', id)
  showThemes.value = false
}

async function copyPrompt() {
  if (!store.output) return
  await navigator.clipboard.writeText(store.output)
  copied.value = true
  window.setTimeout(() => (copied.value = false), 1600)
}

function example() {
  store.topic = '帮我为一款面向大学生的习惯养成 App 写一组小红书推广文案'
  store.context = '产品特点：轻量打卡、伙伴监督、每周复盘。目标是让用户愿意下载并开始连续使用。'
  store.audience = '正在尝试建立学习和生活习惯的大学生'
}
</script>

<template>
  <main class="workspace-shell">
    <header class="topbar">
      <a class="brand" href="#" aria-label="Prompt Studio 首页">
        <span class="brand-mark"><WandSparkles :size="18" /></span>
        <span class="brand-name">Prompt Studio</span>
        <span class="brand-divider"></span>
        <span class="brand-caption">提示词工作台</span>
      </a>
      <div class="top-actions">
        <button class="theme-trigger" type="button" @click="showThemes = !showThemes" aria-label="切换背景" title="切换背景">
          <Palette :size="17" /><span>背景</span><ChevronDown :size="14" />
        </button>
        <div v-if="showThemes" class="theme-menu" role="menu">
          <button v-for="theme in themes" :key="theme.id" class="theme-option" :class="{ chosen: store.theme === theme.id }" @click="setTheme(theme.id)">
            <span class="theme-swatch" :style="{ background: theme.color, color: theme.ink }"><Check v-if="store.theme === theme.id" :size="13" /></span>
            {{ theme.name }}背景
          </button>
        </div>
        <button class="icon-button" type="button" title="新建提示词" aria-label="新建提示词" @click="store.reset()"><FilePlus2 :size="18" /></button>
        <span class="avatar" aria-label="个人工作区">林</span>
      </div>
    </header>

    <section class="intro-row">
      <div>
        <h1>把你的想法，<span>写成好提示词。</span></h1>
      </div>
      <p class="intro-note">说清楚你要做什么。<br />结构、角色和输出格式，交给工作台整理。</p>
    </section>

    <nav class="workspace-tabs" aria-label="工作区视图">
      <button :class="{ active: activeTab === 'compose' }" @click="activeTab = 'compose'"><WandSparkles :size="16" /> 提示词生成</button>
      <button :class="{ active: activeTab === 'settings' }" @click="activeTab = 'settings'"><KeyRound :size="16" /> 模型设置</button>
      <button :class="{ active: activeTab === 'history' }" @click="activeTab = 'history'"><History :size="16" /> 最近记录</button>
      <span class="tab-tail">{{ store.isStreaming ? '正在生成' : '草稿自动保存在本次会话' }}</span>
    </nav>

    <section v-if="activeTab === 'compose'" class="editor-grid">
      <form class="input-panel" data-ui @submit.prevent="store.generate()">
        <div class="panel-heading">
          <div><h2>描述你的任务</h2><p>先写下核心目标，其余信息可以逐步补充。</p></div>
          <button class="text-action" type="button" @click="example"><Lightbulb :size="15" /> 试试示例</button>
        </div>

        <label class="field-block">
          <span class="field-label">你想让 AI 帮你做什么 <b>必填</b></span>
          <textarea v-model="store.topic" required rows="3" placeholder="例如：为一款面向大学生的习惯养成 App 写一组推广文案"></textarea>
          <span class="field-hint">一句话说清楚任务即可，不需要先懂提示词。</span>
        </label>

        <label class="field-block">
          <span class="field-label">补充背景 <i>选填</i></span>
          <textarea v-model="store.context" rows="3" placeholder="产品、使用场景、限制条件或你已有的素材"></textarea>
        </label>

        <label class="field-block">
          <span class="field-label">面向谁使用 <i>选填</i></span>
          <input v-model="store.audience" type="text" placeholder="例如：第一次接触理财的年轻人" />
        </label>

        <div class="form-controls">
          <label class="select-control">
            <span>提示词风格</span>
            <select v-model="store.style">
              <option value="balanced">清晰均衡</option>
              <option value="detailed">细节充分</option>
              <option value="concise">简洁直接</option>
              <option value="creative">创意发散</option>
            </select>
            <ChevronDown :size="14" />
          </label>
          <label class="toggle-control">
            <input v-model="store.includeVariables" type="checkbox" />
            <span class="toggle-track"><span></span></span>
            <span>保留可替换变量</span>
          </label>
        </div>

        <button class="generate-button" type="submit" :disabled="store.isStreaming || !store.topic.trim()">
          <LoaderCircle v-if="store.isStreaming" class="spin" :size="18" />
          <Sparkles v-else :size="18" />
          {{ store.isStreaming ? '正在整理提示词…' : '生成我的提示词' }}
          <ArrowRight v-if="!store.isStreaming" :size="18" />
        </button>
        <p class="privacy-note"><span class="privacy-dot"></span>内容仅用于本次生成，不会保存在服务器</p>
      </form>

      <section class="output-panel" data-ui aria-live="polite">
        <div class="output-head">
          <div><div class="output-title"><h2>你的提示词</h2><span v-if="outputReady" class="ready-mark"><Check :size="12" /> 已就绪</span></div><p>{{ outputReady ? `${wordCount} 个词 · 可复制后直接使用` : '生成结果会出现在这里' }}</p></div>
          <div v-if="outputReady" class="output-actions">
            <button class="small-icon-button" type="button" title="重新生成" aria-label="重新生成" :disabled="store.isStreaming" @click="store.generate()"><RotateCcw :size="16" /></button>
            <button class="copy-button" type="button" @click="copyPrompt"><Check v-if="copied" :size="15" /><Copy v-else :size="15" /> {{ copied ? '已复制' : '复制提示词' }}</button>
          </div>
        </div>
        <div v-if="outputReady" class="prompt-output"><pre>{{ store.output }}<span v-if="store.isStreaming" class="cursor"></span></pre></div>
        <div v-else class="empty-output">
          <div class="empty-art" aria-hidden="true"><span class="paper-back"></span><span class="paper-front"><i></i><i></i><i></i><b><Sparkles :size="17" /></b></span></div>
          <h3>一份好提示词，从清晰目标开始</h3>
          <p>生成后你会得到角色设定、执行步骤和<br class="desktop-break" />明确的输出格式，可以继续修改或复制使用。</p>
          <span class="output-caption"><Clipboard :size="14" /> 可直接用于 ChatGPT、Claude 等 AI 工具</span>
        </div>
        <div v-if="store.error" class="error-message" role="alert">{{ store.error }}</div>
        <footer class="output-footer"><span><span class="status-dot"></span> {{ store.backendMode === 'api' ? 'AI 服务已连接' : '本地演示模式' }}</span><button type="button" @click="store.generate()" :disabled="!store.topic.trim() || store.isStreaming">再优化一次 <ArrowDown :size="13" /></button></footer>
      </section>
    </section>

    <section v-else-if="activeTab === 'settings'" class="settings-view" data-ui>
      <div class="settings-heading">
        <div><h2>连接你的大模型</h2><p>选择服务商并填写 API Key，即可使用真实模型生成提示词。</p></div>
        <span class="settings-state" :class="store.modelApiKey ? 'configured' : 'demo-state'"><span></span>{{ store.modelApiKey ? '页面会话中已填写' : '当前使用本地演示' }}</span>
      </div>
      <div class="settings-columns">
        <div class="settings-form">
          <label class="settings-field"><span>模型服务商</span>
            <select :value="store.modelProvider" @change="store.chooseProvider(($event.target as HTMLSelectElement).value)">
              <option v-for="provider in store.providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option>
            </select>
          </label>
          <label class="settings-field"><span>API Key</span>
            <div class="key-input-wrap"><KeyRound :size="16" /><input v-model="store.modelApiKey" :type="revealKey ? 'text' : 'password'" autocomplete="new-password" spellcheck="false" placeholder="粘贴服务商提供的 API Key" /><button type="button" :aria-label="revealKey ? '隐藏密钥' : '显示密钥'" @click="revealKey = !revealKey"><EyeOff v-if="revealKey" :size="17" /><Eye v-else :size="17" /></button></div>
          </label>
          <div class="settings-field-pair">
            <label class="settings-field"><span>模型名称</span><input v-model="store.modelName" autocomplete="off" placeholder="填写服务商提供的模型 ID" /></label>
            <label class="settings-field"><span>API 接口地址</span><input v-model="store.modelBaseUrl" autocomplete="url" placeholder="填写服务商提供的 HTTPS 接口地址" /></label>
          </div>
          <div class="settings-buttons">
            <button class="test-connection" type="button" :disabled="store.modelTestState === 'testing'" @click="store.testModel()"><LoaderCircle v-if="store.modelTestState === 'testing'" class="spin" :size="16" /><CircleCheck v-else :size="16" /> {{ store.modelTestState === 'testing' ? '测试中…' : '测试连接' }}</button>
            <button v-if="store.modelApiKey" class="clear-key" type="button" @click="store.clearModelKey()">清除密钥</button>
          </div>
          <p v-if="store.modelTestMessage" class="connection-result" :class="store.modelTestState"><CircleCheck v-if="store.modelTestState === 'success'" :size="16" /><CircleAlert v-else-if="store.modelTestState === 'error'" :size="16" /><LoaderCircle v-else-if="store.modelTestState === 'testing'" class="spin" :size="16" />{{ store.modelTestMessage }}</p>
        </div>
        <aside class="key-notice">
          <div class="notice-icon"><ShieldCheck :size="21" /></div>
          <h3>密钥由你掌控</h3>
          <p>API Key 只保存在当前页面内存中。生成或测试时会通过本地后端转发给你选择的模型服务商，不会写入数据库或浏览器存储。</p>
          <p>请只在可信的本地环境使用。若部署到网络，务必启用 HTTPS；请求会把你的任务内容发送给对应模型服务商。</p>
          <span><span class="notice-dot"></span> {{ store.modelApiKey ? '已填写密钥，生成时将调用所选模型' : '不填写密钥仍可用演示模式体验' }}</span>
        </aside>
      </div>
      <div class="provider-note"><strong>服务商预设</strong><span>OpenAI · DeepSeek · 通义千问 · 硅基流动 · Kimi · 智谱 · OpenRouter · 自定义兼容接口</span></div>
    </section>

    <section v-else class="history-view">
      <div class="panel-heading"><div><h2>最近记录</h2><p>本地会话记录将在你生成提示词后显示。</p></div><button class="text-action" @click="activeTab = 'compose'">返回生成 <ArrowRight :size="15" /></button></div>
      <div v-if="store.history.length" class="history-list"><button v-for="item in store.history" :key="item.id" class="history-item" @click="store.loadHistory(item)"><span><strong>{{ item.topic }}</strong><small>{{ item.date }} · {{ item.style }}</small></span><ArrowRight :size="16" /></button></div>
      <div v-else class="history-empty"><History :size="22" /><span>还没有生成记录</span><button @click="activeTab = 'compose'">开始创建 <ArrowRight :size="14" /></button></div>
    </section>

    <footer class="page-footer"><span>Prompt Studio</span><span>让每一次提问，都更接近你想要的答案。</span><a href="https://platform.openai.com/docs" target="_blank" rel="noreferrer">关于提示词 <ArrowRight :size="13" /></a></footer>
  </main>
</template>
