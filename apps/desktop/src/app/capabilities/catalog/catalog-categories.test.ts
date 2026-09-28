import { describe, expect, it } from 'vitest'

import type { CatalogEntry } from './catalog-data'
import { catalogCategories } from './catalog-query'

const entry = (category: string, categoryLabel = category): CatalogEntry =>
  ({ category, categoryLabel }) as CatalogEntry

const many = (n: number) => Array.from({ length: n }, (_, i) => entry(`cat-${i}`, `Cat ${i}`))

describe('catalogCategories', () => {
  it('returns every row when no limit is given', () => {
    expect(catalogCategories(many(30), 'skills')).toHaveLength(30)
  })

  it('caps the rail at the limit, highest count first', () => {
    const rows = catalogCategories(many(30), 'skills', [], 12)

    expect(rows).toHaveLength(12)
    // every entry has count 1, so the order is the input order
    expect(rows[0][0]).toBe('cat-0')
  })

  it('keeps a selected category that fell below the cut', () => {
    // The regression this pins: a filter applied by a deep link, or one the
    // user set and then narrowed, must never become impossible to CLEAR -
    // the row has to still be on the rail even though it is not in the top N.
    const rows = catalogCategories(many(30), 'skills', ['cat-25'], 12)
    const values = rows.map(([value]) => value)

    expect(values).toContain('cat-25')
    expect(rows).toHaveLength(13)
  })

  it('does not duplicate a selected category that is already in the top N', () => {
    const values = catalogCategories(many(30), 'skills', ['cat-3'], 12).map(([value]) => value)

    expect(values).toHaveLength(12)
    expect(values.filter(v => v === 'cat-3')).toHaveLength(1)
  })

  it('ignores a selected category that is not in the catalog', () => {
    const rows = catalogCategories(many(30), 'skills', ['not-a-category'], 12)

    expect(rows).toHaveLength(12)
  })

  it('keeps counts on the rows it returns', () => {
    const entries = [entry('a'), entry('a'), entry('b')]
    const rows = catalogCategories(entries, 'skills', [], 1)

    expect(rows).toHaveLength(1)
    expect(rows[0][1].count).toBe(2)
  })

  it('orders by count before applying the limit', () => {
    const entries = [entry('rare'), ...Array.from({ length: 5 }, () => entry('common'))]
    const rows = catalogCategories(entries, 'skills', [], 1)

    expect(rows[0][0]).toBe('common')
  })
})
