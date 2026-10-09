/// <reference types="node" />
/** La liste des tables brutes est celle du serveur (`services/donnees_brutes.TABLES`), une seule déclaration. */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

import { expect, it } from 'vitest'

import { TABLES } from './DonneesBrutes'

it('les tables proposées sont celles de la liste fermée du serveur', () => {
  const source = readFileSync(
    join(process.cwd(), '..', 'backend', 'gestion_mp_pro', 'services', 'donnees_brutes.py'),
    'utf8',
  )
  const bloc = source.slice(source.indexOf('TABLES = ('), source.indexOf(')', source.indexOf('TABLES = (')))
  expect([...bloc.matchAll(/"(\w+)"/g)].map((m) => m[1])).toEqual([...TABLES])
})
