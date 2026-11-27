/**
 * plugins/vuetify.ts
 *
 * Framework documentation: https://vuetifyjs.com
 *
 * Color scheme: Flexoki by Steph Ango
 * https://stephango.com/flexoki
 * MIT License, Copyright (c) 2023 Steph Ango
 */

import { createVuetify, type ThemeDefinition } from 'vuetify'
// Styles
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

/**
 * Flexoki palette (v2.0), only the values used below.
 * Source: https://stephango.com/flexoki
 */
const flexoki = {
  paper: '#FFFCF0',
  black: '#100F0F',
  base: {
    50: '#F2F0E5',
    100: '#E6E4D9',
    150: '#DAD8CE',
    200: '#CECDC3',
    300: '#B7B5AC',
    500: '#878580',
    600: '#6F6E69',
    700: '#575653',
    800: '#403E3C',
    850: '#343331',
    900: '#282726',
    950: '#1C1B1A',
  },
  red: { 400: '#D14D41', 600: '#AF3029' },
  orange: { 400: '#DA702C', 600: '#BC5215' },
  green: { 400: '#879A39', 600: '#66800B' },
  cyan: { 400: '#3AA99F', 500: '#2F968D', 600: '#24837B', 700: '#1C6C66' },
  blue: { 400: '#4385BE', 600: '#205EA6' },
  purple: { 400: '#8B7EC8', 500: '#735EB5', 600: '#5E409D', 700: '#4F3685' },
} as const

/**
 * Light: "a sheet of paper on a desk".
 * background = bg-2, surface (cards, sheets, editor) = bg (paper).
 * Accents use the 600 values, as Flexoki recommends for light themes.
 */
const flexokiLight: ThemeDefinition = {
  dark: false,
  colors: {
    'background': flexoki.base[50], // bg-2
    'surface': flexoki.paper, // bg
    'surface-bright': flexoki.paper,
    'surface-light': flexoki.base[100], // ui
    'surface-variant': flexoki.base[800], // tooltips, snackbars
    'on-surface-variant': flexoki.base[50],

    'on-background': flexoki.black, // tx
    'on-surface': flexoki.black, // tx

    'primary': flexoki.cyan[600], // cy: links, active states
    'primary-darken-1': flexoki.cyan[700],
    'secondary': flexoki.purple[600],
    'secondary-darken-1': flexoki.purple[700],
    'error': flexoki.red[600], // re
    'warning': flexoki.orange[600], // or
    'success': flexoki.green[600], // gr
    'info': flexoki.blue[600], // bl

    'on-primary': flexoki.paper,
    'on-secondary': flexoki.paper,
    'on-error': flexoki.paper,
    'on-warning': flexoki.paper,
    'on-success': flexoki.paper,
    'on-info': flexoki.paper,
  },
  variables: {
    'border-color': flexoki.base[150], // ui-2
    'border-opacity': 0.2,
    'high-emphasis-opacity': 1, // tx at full strength
    'medium-emphasis-opacity': 0.6, // ≈ tx-2 (base-600)
    'theme-code': flexoki.base[50],
    'theme-on-code': flexoki.black,
    'theme-kbd': flexoki.base[800],
    'theme-on-kbd': flexoki.paper,
  },
}

/**
 * Dark: background = black (bg), surface = base-950 (bg-2),
 * so elevated surfaces read slightly lighter, as in Material dark themes.
 * Accents use the 400 values, as Flexoki recommends for dark themes.
 */
const flexokiDark: ThemeDefinition = {
  dark: true,
  colors: {
    'background': flexoki.black, // bg
    'surface': flexoki.base[950], // bg-2
    'surface-bright': flexoki.base[850],
    'surface-light': flexoki.base[900], // ui
    'surface-variant': flexoki.base[200], // tooltips, snackbars
    'on-surface-variant': flexoki.base[950],

    'on-background': flexoki.base[200], // tx
    'on-surface': flexoki.base[200], // tx

    'primary': flexoki.cyan[400],
    'primary-darken-1': flexoki.cyan[500],
    'secondary': flexoki.purple[400],
    'secondary-darken-1': flexoki.purple[500],
    'error': flexoki.red[400],
    'warning': flexoki.orange[400],
    'success': flexoki.green[400],
    'info': flexoki.blue[400],

    'on-primary': flexoki.black,
    'on-secondary': flexoki.black,
    'on-error': flexoki.black,
    'on-warning': flexoki.black,
    'on-success': flexoki.black,
    'on-info': flexoki.black,
  },
  variables: {
    'border-color': flexoki.base[850], // ui-2
    'border-opacity': 0.2,
    'high-emphasis-opacity': 1,
    'medium-emphasis-opacity': 0.6, // ≈ tx-2 (base-500)
    'theme-code': flexoki.base[900],
    'theme-on-code': flexoki.base[200],
    'theme-kbd': flexoki.base[850],
    'theme-on-kbd': flexoki.base[200],
  },
}

// https://vuetifyjs.com/en/introduction/why-vuetify/#feature-guides
export default createVuetify({
  theme: {
    defaultTheme: 'light',
    themes: {
      light: flexokiLight,
      dark: flexokiDark,
    },
  },
})
