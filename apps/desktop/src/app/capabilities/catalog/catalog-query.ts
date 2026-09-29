import { PLUGIN_CATEGORIES, PLUGIN_CATEGORY_ORDER, sortCatalogPlugins } from '@kova/shared'

import type { CatalogEntry, CatalogKind } from './catalog-data'
import type { FacetRow } from './catalog-filters'

export type CatalogSort = 'discover' | 'stars' | 'newest' | 'updated' | 'name'

export interface CatalogFacets {
  sources: string[]
  categories: string[]
  tags: string[]
  installedOnly: boolean
}

export const EMPTY_FACETS: CatalogFacets = { sources: [], categories: [], tags: [], installedOnly: false }

export const catalogSources = (entries: CatalogEntry[]) => [...new Set(entries.map(entry => entry.source))]

/**
 * Category facet rows with counts; plugins follow the shared taxonomy order.
 *
 * `limit` caps the RAIL, exactly as `catalogTags` already caps tags: the
 * rail is for browsing and the search above it covers the tail. Without it
 * the skills catalog rendered 30 category rows - the last 8 of them starting
 * at y=915 in a 925px window - and because the rail's scrollbar is not
 * visible it read as ending at "Web". Anything selected is always kept, so a
 * filter the user (or a deep link) already applied can never scroll out of
 * reach and become impossible to clear.
 */
export function catalogCategories(
  entries: CatalogEntry[],
  kind: CatalogKind,
  selected: readonly string[] = [],
  limit = Number.POSITIVE_INFINITY
) {
  const values = new Map<string, { label: string; count: number }>()

  for (const entry of entries) {
    values.set(entry.category, { label: entry.categoryLabel, count: (values.get(entry.category)?.count ?? 0) + 1 })
  }

  let rows: ReadonlyArray<readonly [string, { label: string; count: number }]>

  if (kind === 'plugins') {
    rows = PLUGIN_CATEGORY_ORDER.filter(key => values.has(key)).map(
      key => [key, { ...values.get(key)!, label: PLUGIN_CATEGORIES[key].label }] as const
    )
  } else {
    rows = [...values].sort((a, b) => b[1].count - a[1].count)
  }

  if (rows.length <= limit) {
    return rows
  }

  // Keep the top `limit` by rank, then re-add anything selected that fell
  // below the cut. Appended in the order they were selected so the list does
  // not reshuffle as the user toggles.
  const keep = new Set(rows.slice(0, limit).map(([value]) => value))
  const restored = selected.filter(value => !keep.has(value) && values.has(value))

  return [...rows.slice(0, limit), ...restored.map(value => [value, values.get(value)!] as const)]
}

/** The most common tags plus whatever is selected; search covers the long tail. */
export function catalogTags(entries: CatalogEntry[], selected: string[], limit: number): FacetRow[] {
  const counts = new Map<string, number>()

  for (const entry of entries) {
    for (const value of new Set(entry.tags)) {
      counts.set(value, (counts.get(value) ?? 0) + 1)
    }
  }

  const ranked = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  const shown = new Set([...ranked.slice(0, limit).map(([value]) => value), ...selected])

  return ranked.filter(([value]) => shown.has(value)).map(([value, count]) => ({ value, label: value, count }))
}

/** Facets combine as AND across groups and OR within one. */
export function filterCatalog(
  entries: CatalogEntry[],
  facets: CatalogFacets,
  query: string,
  isInstalled: (entry: CatalogEntry) => boolean
) {
  const { sources, categories, tags, installedOnly } = facets

  return entries.filter(
    entry =>
      (!sources.length || sources.includes(entry.source)) &&
      (!categories.length || categories.includes(entry.category)) &&
      (!tags.length || tags.some(tag => entry.tags.includes(tag))) &&
      (!installedOnly || isInstalled(entry)) &&
      (!query || entry.search.includes(query))
  )
}

/** Returns a new array; `discover` keeps the feed's curated order. */
export function sortCatalog(entries: CatalogEntry[], sort: CatalogSort, kind: CatalogKind) {
  if (sort === 'discover') {
    return entries
  }

  if (kind === 'plugins' && sort !== 'name') {
    return sortCatalogPlugins(entries, sort)
  }

  if (sort === 'name') {
    return [...entries].sort((a, b) => a.name.localeCompare(b.name))
  }

  if (sort === 'stars') {
    return [...entries].sort((a, b) => (b.stars ?? -1) - (a.stars ?? -1) || a.name.localeCompare(b.name))
  }

  const field = sort === 'newest' ? 'addedAt' : 'updatedAt'
  const time = new Map(entries.map(entry => [entry.id, Date.parse(entry[field] ?? '') || 0]))

  return [...entries].sort((a, b) => time.get(b.id)! - time.get(a.id)! || a.name.localeCompare(b.name))
}

/** First `limit` entries sharing a category or tag with `entry`; stops early on large feeds. */
export function relatedEntries(entries: CatalogEntry[], entry: CatalogEntry, limit: number) {
  const matches: CatalogEntry[] = []

  for (const candidate of entries) {
    if (matches.length === limit) {
      break
    }

    if (
      candidate.id !== entry.id &&
      (candidate.category === entry.category || candidate.tags.some(tag => entry.tags.includes(tag)))
    ) {
      matches.push(candidate)
    }
  }

  return matches
}

export function catalogSortOptions(entries: CatalogEntry[], kind: CatalogKind, labels: Record<CatalogSort, string>) {
  const available: Record<CatalogSort, boolean> = {
    discover: kind === 'skills',
    stars: entries.some(entry => entry.stars !== null),
    newest: entries.some(entry => entry.addedAt),
    updated: entries.some(entry => entry.updatedAt),
    name: kind === 'skills'
  }

  return (Object.keys(available) as CatalogSort[])
    .filter(value => available[value])
    .map(value => ({ value, label: labels[value] }))
}
