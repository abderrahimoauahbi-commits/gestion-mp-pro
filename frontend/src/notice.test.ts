/// <reference types="node" />
/** docs/NOTICE.md est générée depuis aide.json (scripts/generer_notice.py) : elle doit être à jour. */
import { execFileSync } from 'node:child_process'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const RACINE = join(dirname(fileURLToPath(import.meta.url)), '..', '..')

describe('NOTICE', () => {
  it('docs/NOTICE.md est à jour avec aide.json', () => {
    expect(() =>
      execFileSync('python3', [join(RACINE, 'scripts', 'generer_notice.py'), '--verifier'], {
        stdio: 'pipe',
      }),
    ).not.toThrow()
  })
})
