// Feuilles de style de l'écran (ARCHITECTURE § 9.2, ECRANS-PRO § 3) : aucune couleur hors de
// `src/styles/jetons.css`. Partout ailleurs, une couleur s'écrit `var(--jeton)`.
export default {
  extends: ['stylelint-config-standard'],
  rules: {
    'color-no-hex': true,
    'color-named': 'never',
    'function-disallowed-list': [
      'rgb',
      'rgba',
      'hsl',
      'hsla',
      'hwb',
      'lab',
      'lch',
      'oklab',
      'oklch',
      'color',
    ],
    // Les classes des modules CSS s'écrivent en camelCase (`styles.ligneCliquable`).
    'selector-class-pattern': [
      '^[a-z][a-zA-Z0-9]*(-[a-zA-Z0-9]+)*$',
      { message: 'Classe en camelCase ou en minuscules-avec-tirets.' },
    ],
    'custom-property-pattern': [
      '^[a-z][a-z0-9]*(-[a-z0-9]+)*$',
      { message: 'Jeton en minuscules-avec-tirets (--texte-2).' },
    ],
    'keyframes-name-pattern': '^[a-z][a-zA-Z0-9]*$',
    'value-keyword-case': ['lower', { camelCaseSvgKeywords: true, ignoreKeywords: ['/^[A-Z]/'] }],
  },
  overrides: [
    {
      files: ['src/styles/jetons.css'],
      rules: {
        'color-no-hex': null,
        'color-named': null,
        'function-disallowed-list': null,
      },
    },
  ],
}
