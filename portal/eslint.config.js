import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Allow any in specific cases (existing code)
      '@typescript-eslint/no-explicit-any': 'warn',
      // Relax react-refresh for utility files that export hooks/functions
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true, allowExportNames: ['useAuth', 'useTheme', 'badgeVariants', 'buttonVariants'] },
      ],
      // Disable the setState in effect rule - this pattern is used in the codebase
      'react-hooks/set-state-in-effect': 'off',
    },
  },
  // Test file overrides
  {
    files: ['**/__tests__/**/*.{ts,tsx}', '**/*.test.{ts,tsx}'],
    rules: {
      // Allow exports from test utility files
      'react-refresh/only-export-components': 'off',
      // Allow any in test mocks
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
])
