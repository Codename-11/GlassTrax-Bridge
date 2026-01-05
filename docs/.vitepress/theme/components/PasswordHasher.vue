<script setup lang="ts">
import { ref, computed } from 'vue'
import bcrypt from 'bcryptjs'

const password = ref('')
const hash = ref('')
const isHashing = ref(false)
const copied = ref(false)
const showPassword = ref(false)

const isValid = computed(() => password.value.length >= 1)

async function generateHash() {
  if (!isValid.value) return

  isHashing.value = true
  hash.value = ''
  copied.value = false

  // Use setTimeout to allow UI to update before blocking hash operation
  await new Promise(resolve => setTimeout(resolve, 50))

  try {
    const salt = bcrypt.genSaltSync(12)
    hash.value = bcrypt.hashSync(password.value, salt)
  } catch (error) {
    hash.value = 'Error generating hash'
  } finally {
    isHashing.value = false
  }
}

async function copyToClipboard() {
  if (!hash.value) return

  try {
    await navigator.clipboard.writeText(hash.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (error) {
    // Fallback for older browsers
    const textarea = document.createElement('textarea')
    textarea.value = hash.value
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  }
}
</script>

<template>
  <div class="password-hasher">
    <div class="input-group">
      <label for="password-input">Password</label>
      <div class="input-wrapper">
        <input
          id="password-input"
          v-model="password"
          :type="showPassword ? 'text' : 'password'"
          placeholder="Enter password to hash"
          @keyup.enter="generateHash"
        />
        <button
          type="button"
          class="toggle-visibility"
          @click="showPassword = !showPassword"
          :title="showPassword ? 'Hide password' : 'Show password'"
        >
          {{ showPassword ? '👁️' : '👁️‍🗨️' }}
        </button>
      </div>
    </div>

    <button
      class="generate-btn"
      :disabled="!isValid || isHashing"
      @click="generateHash"
    >
      {{ isHashing ? 'Generating...' : 'Generate bcrypt Hash' }}
    </button>

    <div v-if="hash" class="result">
      <label>bcrypt Hash (cost factor: 12)</label>
      <div class="hash-output">
        <code>{{ hash }}</code>
        <button
          class="copy-btn"
          @click="copyToClipboard"
          :title="copied ? 'Copied!' : 'Copy to clipboard'"
        >
          {{ copied ? '✓' : '📋' }}
        </button>
      </div>
      <p class="hint">
        Copy this hash and paste it into your <code>config.yaml</code> under <code>admin.password_hash</code>
      </p>
    </div>

    <div class="security-note">
      <strong>Security Note:</strong> This hash is generated entirely in your browser.
      Your password is never sent to any server.
    </div>
  </div>
</template>

<style scoped>
.password-hasher {
  border: 1px solid var(--vp-c-divider);
  border-radius: 8px;
  padding: 20px;
  margin: 16px 0;
  background: var(--vp-c-bg-soft);
}

.input-group {
  margin-bottom: 16px;
}

.input-group label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--vp-c-text-1);
}

.input-wrapper {
  display: flex;
  gap: 8px;
}

.input-wrapper input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  font-size: 14px;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-1);
}

.input-wrapper input:focus {
  outline: none;
  border-color: var(--vp-c-brand-1);
}

.toggle-visibility {
  padding: 8px 12px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg);
  cursor: pointer;
  font-size: 16px;
}

.toggle-visibility:hover {
  background: var(--vp-c-bg-mute);
}

.generate-btn {
  width: 100%;
  padding: 12px 20px;
  background: var(--vp-c-brand-1);
  color: var(--vp-c-white);
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.generate-btn:hover:not(:disabled) {
  background: var(--vp-c-brand-2);
}

.generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.result {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--vp-c-divider);
}

.result label {
  display: block;
  margin-bottom: 8px;
  font-weight: 600;
  color: var(--vp-c-text-1);
}

.hash-output {
  display: flex;
  gap: 8px;
  align-items: stretch;
}

.hash-output code {
  flex: 1;
  padding: 12px;
  background: var(--vp-c-bg);
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  font-size: 12px;
  word-break: break-all;
  font-family: var(--vp-font-family-mono);
}

.copy-btn {
  padding: 8px 16px;
  border: 1px solid var(--vp-c-divider);
  border-radius: 6px;
  background: var(--vp-c-bg);
  cursor: pointer;
  font-size: 16px;
  transition: background 0.2s;
}

.copy-btn:hover {
  background: var(--vp-c-bg-mute);
}

.hint {
  margin-top: 12px;
  font-size: 13px;
  color: var(--vp-c-text-2);
}

.hint code {
  background: var(--vp-c-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.security-note {
  margin-top: 16px;
  padding: 12px;
  background: var(--vp-c-tip-bg);
  border-radius: 6px;
  font-size: 13px;
  color: var(--vp-c-tip-text);
  border-left: 4px solid var(--vp-c-tip-1);
}

.security-note strong {
  color: var(--vp-c-tip-1);
}
</style>
