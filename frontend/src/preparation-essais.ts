/** Préparation commune des essais (vitest + Testing Library + jsdom). */
import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

import { reinitialiserHorloge } from './lib/heure'

afterEach(() => {
  cleanup()
  reinitialiserHorloge()
})
