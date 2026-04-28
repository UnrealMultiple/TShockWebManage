import { reactive } from 'vue'

let nextToastId = 1

const state = reactive({
  toasts: [],
  dialog: null,
})

function pushToast(type, message, options = {}) {
  const text = String(message || '').trim()
  if (!text) return null
  const id = nextToastId++
  const toast = {
    id,
    type,
    title: options.title || '',
    message: text,
  }
  state.toasts.push(toast)
  window.setTimeout(() => removeToast(id), Number(options.duration || 3200))
  return id
}

function removeToast(id) {
  const idx = state.toasts.findIndex(t => t.id === id)
  if (idx >= 0) state.toasts.splice(idx, 1)
}

function openDialog(config) {
  return new Promise(resolve => {
    state.dialog = {
      type: config.type || 'confirm',
      title: config.title || '',
      message: config.message || '',
      label: config.label || '',
      placeholder: config.placeholder || '',
      value: config.defaultValue || '',
      required: !!config.required,
      danger: !!config.danger,
      confirmText: config.confirmText || '确定',
      cancelText: config.cancelText || '取消',
      resolve,
    }
  })
}

function closeDialog(result) {
  if (!state.dialog) return
  const resolver = state.dialog.resolve
  state.dialog = null
  resolver(result)
}

export function useFeedback() {
  return {
    state,
    toast: {
      success: (message, options) => pushToast('success', message, options),
      error: (message, options) => pushToast('error', message, options),
      info: (message, options) => pushToast('info', message, options),
      warning: (message, options) => pushToast('warning', message, options),
      remove: removeToast,
    },
    dialog: {
      alert: ({ title = '提示', message = '', confirmText = '知道了' } = {}) =>
        openDialog({ type: 'alert', title, message, confirmText }).then(() => true),
      confirm: ({ title = '确认操作', message = '', confirmText = '确定', cancelText = '取消', danger = false } = {}) =>
        openDialog({ type: 'confirm', title, message, confirmText, cancelText, danger }),
      prompt: ({
        title = '填写内容',
        message = '',
        label = '',
        placeholder = '',
        defaultValue = '',
        required = false,
        confirmText = '确定',
        cancelText = '取消',
        danger = false,
      } = {}) => openDialog({
        type: 'prompt',
        title,
        message,
        label,
        placeholder,
        defaultValue,
        required,
        confirmText,
        cancelText,
        danger,
      }),
      close: closeDialog,
    },
  }
}
