<template>
  <teleport to="body">
    <div class="fb-toast-stack" aria-live="polite">
      <div v-for="item in state.toasts" :key="item.id" :class="['fb-toast', `fb-toast-${item.type}`]">
        <div class="fb-toast-icon">
          <svg v-if="item.type === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M20 6 9 17l-5-5"/>
          </svg>
          <svg v-else-if="item.type === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>
          </svg>
          <svg v-else-if="item.type === 'warning'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
          </svg>
        </div>
        <div class="fb-toast-body">
          <div v-if="item.title" class="fb-toast-title">{{ item.title }}</div>
          <div class="fb-toast-message">{{ item.message }}</div>
        </div>
        <button class="fb-toast-close" type="button" @click="toast.remove(item.id)" aria-label="关闭">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
          </svg>
        </button>
      </div>
    </div>

    <div v-if="state.dialog" class="fb-dialog-layer" @click.self="cancelDialog">
      <div class="fb-dialog" role="dialog" aria-modal="true">
        <div class="fb-dialog-head">
          <div class="fb-dialog-mark">
            <svg v-if="state.dialog.danger" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
            </svg>
          </div>
          <div>
            <h3 class="fb-dialog-title">{{ state.dialog.title }}</h3>
            <p v-if="state.dialog.message" class="fb-dialog-message">{{ state.dialog.message }}</p>
          </div>
        </div>

        <label v-if="state.dialog.type === 'prompt'" class="fb-prompt-field">
          <span v-if="state.dialog.label">{{ state.dialog.label }}</span>
          <textarea
            v-model.trim="state.dialog.value"
            class="fb-prompt-input"
            rows="4"
            :placeholder="state.dialog.placeholder"
            @keydown.ctrl.enter.prevent="submitPrompt"
          ></textarea>
        </label>

        <div class="fb-dialog-actions">
          <button v-if="state.dialog.type !== 'alert'" class="fb-btn fb-btn-outline" type="button" @click="cancelDialog">
            {{ state.dialog.cancelText }}
          </button>
          <button :class="['fb-btn', state.dialog.danger ? 'fb-btn-danger' : 'fb-btn-primary']" type="button" @click="confirmDialog">
            {{ state.dialog.confirmText }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { useFeedback } from '@/composables/useFeedback'

const { state, toast, dialog } = useFeedback()

function cancelDialog() {
  dialog.close(state.dialog?.type === 'prompt' ? null : false)
}

function confirmDialog() {
  if (!state.dialog) return
  if (state.dialog.type === 'prompt') {
    submitPrompt()
    return
  }
  dialog.close(true)
}

function submitPrompt() {
  if (!state.dialog) return
  const value = String(state.dialog.value || '').trim()
  if (state.dialog.required && !value) return
  dialog.close(value)
}
</script>

<style scoped>
.fb-toast-stack {
  position: fixed;
  top: 18px;
  right: 18px;
  z-index: 5000;
  display: grid;
  gap: 10px;
  width: min(380px, calc(100vw - 32px));
}

.fb-toast {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: start;
  gap: 10px;
  padding: 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 16px 36px rgba(15, 23, 42, .14);
  color: #0f172a;
}

.fb-toast-icon svg,
.fb-toast-close svg,
.fb-dialog-mark svg {
  width: 18px;
  height: 18px;
}

.fb-toast-success { border-color: #bbf7d0; }
.fb-toast-success .fb-toast-icon { color: #15803d; }
.fb-toast-error { border-color: #fecaca; }
.fb-toast-error .fb-toast-icon { color: #dc2626; }
.fb-toast-warning { border-color: #fde68a; }
.fb-toast-warning .fb-toast-icon { color: #d97706; }
.fb-toast-info .fb-toast-icon { color: #2563eb; }

.fb-toast-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 2px;
}

.fb-toast-message {
  font-size: 13px;
  line-height: 1.45;
  white-space: pre-wrap;
}

.fb-toast-close {
  border: 0;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  padding: 1px;
}

.fb-dialog-layer {
  position: fixed;
  inset: 0;
  z-index: 5100;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, .38);
}

.fb-dialog {
  width: min(460px, 100%);
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 24px 70px rgba(15, 23, 42, .28);
  padding: 18px;
}

.fb-dialog-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.fb-dialog-mark {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #eff6ff;
  color: #2563eb;
  flex-shrink: 0;
}

.fb-dialog-title {
  margin: 0;
  font-size: 16px;
  color: #0f172a;
}

.fb-dialog-message {
  margin: 6px 0 0;
  color: #475569;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.fb-prompt-field {
  display: grid;
  gap: 6px;
  margin-top: 14px;
  color: #475569;
  font-size: 13px;
}

.fb-prompt-input {
  resize: vertical;
  min-height: 92px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 9px 10px;
  font: inherit;
  color: #0f172a;
  outline: none;
}

.fb-prompt-input:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, .12);
}

.fb-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.fb-btn {
  border: 1px solid transparent;
  border-radius: 8px;
  padding: 8px 15px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.fb-btn-outline {
  background: #fff;
  border-color: #cbd5e1;
  color: #334155;
}

.fb-btn-primary {
  background: #2563eb;
  color: #fff;
}

.fb-btn-danger {
  background: #dc2626;
  color: #fff;
}
</style>
