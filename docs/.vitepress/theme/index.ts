import DefaultTheme from 'vitepress/theme'
import type { Theme } from 'vitepress'
import PasswordHasher from './components/PasswordHasher.vue'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    // Register global components
    app.component('PasswordHasher', PasswordHasher)
  }
} satisfies Theme
