<template>
  <div class="markdown-editor">
    <div class="editor-toolbar">
      <div class="toolbar-group">
        <span class="toolbar-title">{{ title }}</span>
        <span class="toolbar-subtitle">Markdown</span>
      </div>
      <div class="toolbar-actions">
        <button type="button" class="toolbar-btn" @click="applyFormat('**', '**')" title="Bold">
          <strong>B</strong>
        </button>
        <button type="button" class="toolbar-btn" @click="applyFormat('*', '*')" title="Italic">
          <em>I</em>
        </button>
        <button type="button" class="toolbar-btn" @click="applyFormat('`', '`')" title="Inline code">
          <span class="mono">&lt;/&gt;</span>
        </button>
        <button type="button" class="toolbar-btn" @click="applyList('- ')" title="Bullet list">
          • List
        </button>
        <button type="button" class="toolbar-btn" @click="convertCurrentHtml" title="Convert HTML to Markdown">
          Convert HTML
        </button>
      </div>
    </div>
    <textarea
      ref="textareaRef"
      class="editor-textarea"
      :placeholder="placeholder"
      :value="modelValue"
      :required="required"
      rows="6"
      @input="onInput"
      @paste="handlePaste"
    ></textarea>
    <p class="editor-help">
      Paste HTML content and it will be converted to Markdown automatically.
    </p>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: 'Write in Markdown...'
  },
  required: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Description'
  }
})

const emit = defineEmits(['update:modelValue'])

const textareaRef = ref(null)

const htmlTagRegex = /<\/?[a-z][\s\S]*>/i

function onInput(event) {
  emit('update:modelValue', event.target.value)
}

function updateValue(value, caretOffset = 0) {
  emit('update:modelValue', value)
  nextTick(() => {
    const textarea = textareaRef.value
    if (!textarea) return
    const position = Math.max(0, Math.min(value.length, caretOffset))
    textarea.setSelectionRange(position, position)
    textarea.focus()
  })
}

function applyFormat(prefix, suffix) {
  const textarea = textareaRef.value
  if (!textarea) return
  const start = textarea.selectionStart || 0
  const end = textarea.selectionEnd || 0
  const current = props.modelValue || ''
  const selected = current.slice(start, end)
  const updated = `${current.slice(0, start)}${prefix}${selected}${suffix}${current.slice(end)}`
  const caret = start + prefix.length + selected.length + suffix.length
  updateValue(updated, caret)
}

function applyList(prefix) {
  const textarea = textareaRef.value
  if (!textarea) return
  const start = textarea.selectionStart || 0
  const end = textarea.selectionEnd || 0
  const current = props.modelValue || ''
  const selected = current.slice(start, end) || 'List item'
  const lines = selected.split('\n').map(line => (line ? `${prefix}${line}` : prefix))
  const updated = `${current.slice(0, start)}${lines.join('\n')}${current.slice(end)}`
  const caret = start + lines.join('\n').length
  updateValue(updated, caret)
}

function convertHtmlToMarkdown(html) {
  const parser = new DOMParser()
  const doc = parser.parseFromString(html, 'text/html')

  const convertChildren = (parent, depth = 0) =>
    Array.from(parent.childNodes).map(node => convertNode(node, depth)).join('')

  const convertList = (listNode, depth, ordered) => {
    const items = Array.from(listNode.children)
      .filter(node => node.nodeType === Node.ELEMENT_NODE && node.tagName.toLowerCase() === 'li')
      .map((li, index) => {
        const prefix = `${'  '.repeat(depth)}${ordered ? `${index + 1}. ` : '- '}`
        const content = convertChildren(li, depth + 1).trim()
        const formatted = content.replace(/\n/g, `\n${'  '.repeat(depth)}  `)
        return `${prefix}${formatted}`
      })
    return `${items.join('\n')}\n\n`
  }

  const convertNode = (node, depth = 0) => {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.nodeValue || ''
    }
    if (node.nodeType !== Node.ELEMENT_NODE) {
      return ''
    }
    const tag = node.tagName.toLowerCase()
    switch (tag) {
      case 'br':
        return '\n'
      case 'p':
      case 'div':
        return `${convertChildren(node, depth).trim()}\n\n`
      case 'strong':
      case 'b':
        return `**${convertChildren(node, depth).trim()}**`
      case 'em':
      case 'i':
        return `*${convertChildren(node, depth).trim()}*`
      case 'code':
        return `\`${convertChildren(node, depth).trim()}\``
      case 'pre': {
        const codeText = node.textContent || ''
        return `\`\`\`\n${codeText.trim()}\n\`\`\`\n\n`
      }
      case 'a': {
        const text = convertChildren(node, depth).trim() || node.getAttribute('href') || ''
        const href = node.getAttribute('href') || ''
        return href ? `[${text}](${href})` : text
      }
      case 'h1':
      case 'h2':
      case 'h3':
      case 'h4':
      case 'h5':
      case 'h6': {
        const level = Number(tag.replace('h', '')) || 1
        const prefix = '#'.repeat(level)
        return `${prefix} ${convertChildren(node, depth).trim()}\n\n`
      }
      case 'ul':
        return convertList(node, depth, false)
      case 'ol':
        return convertList(node, depth, true)
      case 'li':
        return `${convertChildren(node, depth).trim()}\n`
      default:
        return convertChildren(node, depth)
    }
  }

  const markdown = convertChildren(doc.body).replace(/\n{3,}/g, '\n\n').trim()
  return markdown
}

function handlePaste(event) {
  const htmlData = event.clipboardData?.getData('text/html')
  if (htmlData) {
    event.preventDefault()
    const markdown = convertHtmlToMarkdown(htmlData)
    const textarea = textareaRef.value
    const start = textarea?.selectionStart || 0
    const end = textarea?.selectionEnd || 0
    const current = props.modelValue || ''
    const updated = `${current.slice(0, start)}${markdown}${current.slice(end)}`
    updateValue(updated, start + markdown.length)
  }
}

function convertCurrentHtml() {
  if (!htmlTagRegex.test(props.modelValue || '')) return
  const markdown = convertHtmlToMarkdown(props.modelValue)
  updateValue(markdown, markdown.length)
}
</script>

<style scoped>
.markdown-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}

.toolbar-group {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.toolbar-title {
  font-weight: 600;
  color: var(--text-primary);
}

.toolbar-subtitle {
  font-size: 12px;
  color: var(--text-secondary);
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
}

.toolbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.toolbar-btn {
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary);
  padding: 6px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toolbar-btn:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  box-shadow: var(--shadow-sm);
}

.mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}

.editor-textarea {
  width: 100%;
  min-height: 140px;
  resize: vertical;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.editor-textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.editor-help {
  margin: 0;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
