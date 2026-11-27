import vuetify from 'eslint-config-vuetify'

const base = await vuetify()

export default [
  ...base,
  {
    files: ['**/*.vue', '**/*.tsx', '**/*.jsx'],
    rules: {
      // Allow the standard Vue `update:modelValue` (and `update:xxxCamelCase`)
      // v-model event names, which are camelCase by convention and would
      // otherwise be rejected by the base kebab-case rule.
      'vue/custom-event-name-casing': ['error', 'kebab-case', {
        ignores: [
          '/^[a-z]+(?:-[a-z]+)*:[a-z]+(?:-[a-z]+)*$/u',
          '/^update:[a-zA-Z][a-zA-Z0-9]*$/u',
        ],
      }],
    },
  },
]
