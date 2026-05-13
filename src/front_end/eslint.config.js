import js from '@eslint/js'
import pluginVue from 'eslint-plugin-vue'
import eslintConfigPrettier from 'eslint-config-prettier'
import eslintPluginPrettier from 'eslint-plugin-prettier'

export default [
  {
    ignores: ['dist/**', 'node_modules/**']
  },
  js.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    files: ['**/*.{js,vue}'],
    plugins: {
      prettier: eslintPluginPrettier
    },
    rules: {
      'prettier/prettier': [
        'error',
        {
          singleQuote: true,
          semi: false,
          tabWidth: 2,
          printWidth: 132,
          trailingComma: 'none'
        }
      ]
    }
  },
  {
    files: ['**/__tests__/**', '**/*.test.js'],
    languageOptions: {
      globals: {
        require: 'readonly',
        global: 'readonly'
      }
    }
  },
  {
    files: ['**/*.mjs'],
    languageOptions: {
      globals: {
        process: 'readonly'
      }
    }
  },
  eslintConfigPrettier
]
