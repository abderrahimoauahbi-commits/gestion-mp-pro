// Règles du code de l'écran (ARCHITECTURE § 9.2).
//
// - Les règles des hooks React sont des erreurs : un hook appelé après un retour anticipé fait
//   tomber l'écran au rendu suivant (la page blanche de « Retour des machines » dans Gestion MP).
// - Plafonds : 400 lignes par fichier, 60 lignes par fonction (hors essais et fichiers générés).
// - Jamais de `window.confirm`, `alert`, `prompt` : un geste se confirme sur la ligne (`Confirmer`).
// - Pas d'assertion de type (`as`) hors des essais : un type se prouve, il ne s'affirme pas.
// - Pas de style écrit en dur dans le JSX (`style={{ color: '#c00' }}`) : les couleurs et les
//   mesures fixes vivent dans les feuilles de style ; seule une mesure calculée passe par `style`.
import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import globals from 'globals'
import tseslint from 'typescript-eslint'

const INTERDITS = [
  {
    selector: "CallExpression[callee.object.name='window'][callee.property.name=/^(confirm|alert|prompt)$/]",
    message: 'Pas de fenêtre du navigateur : confirmer sur la ligne avec le composant Confirmer.',
  },
  {
    selector:
      "JSXAttribute[name.name='style'] > JSXExpressionContainer > ObjectExpression > Property[value.type='Literal']",
    message:
      'Style écrit en dur : le mettre dans la feuille de style (seule une mesure calculée passe par style).',
  },
]

export default tseslint.config(
  { ignores: ['dist/', 'node_modules/', 'public/', 'src/lib/types.gen.ts'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx,js}'],
    languageOptions: { ecmaVersion: 2023, globals: { ...globals.browser } },
    plugins: { 'react-hooks': reactHooks },
    rules: {
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'error',
      'max-lines': ['error', { max: 400, skipBlankLines: false, skipComments: false }],
      'max-lines-per-function': ['error', { max: 60, skipBlankLines: true, skipComments: true }],
      'no-restricted-globals': [
        'error',
        { name: 'confirm', message: 'Confirmer sur la ligne (composant Confirmer).' },
        { name: 'alert', message: 'Dire avec Messages (toast), jamais alert.' },
        { name: 'prompt', message: 'Demander dans une Fenetre, jamais prompt.' },
      ],
      'no-restricted-syntax': ['error', ...INTERDITS],
      '@typescript-eslint/consistent-type-assertions': ['error', { assertionStyle: 'never' }],
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      'no-console': ['error', { allow: ['warn', 'error'] }],
    },
  },
  {
    files: ['**/*.test.{ts,tsx}', 'src/preparation-essais.ts'],
    languageOptions: { globals: { ...globals.browser, ...globals.vitest } },
    rules: {
      'max-lines-per-function': 'off',
      '@typescript-eslint/consistent-type-assertions': 'off',
    },
  },
  {
    files: ['*.config.{js,ts}'],
    languageOptions: { globals: { ...globals.node } },
  },
)
