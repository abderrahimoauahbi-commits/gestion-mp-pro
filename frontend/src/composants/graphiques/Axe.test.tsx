/** Essais de l'axe : graduations, zéro appuyé, unité dite. */
import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { Axe, echelleY } from './Axe'

describe('Axe', () => {
  it('trace une ligne par graduation, le zéro appuyé, et l’unité', () => {
    const marges = { g: 50, d: 10, h: 10, b: 20 }
    const { ticks, y } = echelleY([{ nom: 's', valeurs: [-50, 180] }], 200, marges)
    expect(ticks).toEqual([-100, 0, 100, 200])
    expect(y(200)).toBe(10)
    expect(y(-100)).toBe(180)
    const { container } = render(
      <svg>
        <Axe ticks={ticks} y={y} unite="kg" marges={marges} />
      </svg>,
    )
    expect(container.querySelectorAll('line')).toHaveLength(4)
    expect(container.querySelector('.zero')).not.toBeNull()
    expect(container.textContent).toContain('kg')
  })
})
