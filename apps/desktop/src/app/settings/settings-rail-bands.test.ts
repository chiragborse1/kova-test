import { describe, expect, it } from 'vitest'

import { TRANSLATIONS } from '@/i18n'

import { BAND_ORDER, bandFor, bandRank, SETTINGS_BANDS } from './settings-rail-bands'

const ids = (bands: Record<string, string>) => Object.keys(bands)

describe('settings rail bands', () => {
  it('leaves the first band unlabelled', () => {
    // Model, Chat and Appearance are what a person opens Settings for. A
    // heading above them would label the obvious - which is why OpenClaw's
    // first group has `labelKey: null` too.
    expect(SETTINGS_BANDS['config:model']).toBe('')
    expect(SETTINGS_BANDS['config:chat']).toBe('')
    expect(SETTINGS_BANDS['config:appearance']).toBe('')
  })

  it('sorts the unlabelled band first, not last', () => {
    // The regression this pins: the first band is the EMPTY STRING, so a
    // truthiness test treated it as "no band" and sent Model, Chat and
    // Appearance to the bottom of the rail, under System.
    expect(bandRank(bandFor('config:model'))).toBe(0)
    expect(bandRank(bandFor('config:appearance'))).toBe(0)
    expect(BAND_ORDER[0]).toBe('')
  })

  it('sorts a row with no band last, and still reachable', () => {
    expect(bandFor('config:does-not-exist')).toBeNull()
    expect(bandRank(null)).toBe(BAND_ORDER.length)
  })

  it('tells the unlabelled first band apart from no band at all', () => {
    // '' means "in the first band, no heading"; null means "in no band".
    // Collapsing the two is what pushed the essentials to the bottom.
    expect(bandFor('config:model')).not.toBeNull()
    expect(bandFor('config:model')).not.toBe(bandFor('config:does-not-exist'))
  })

  it('puts every band in a strictly increasing rank', () => {
    const ranks = BAND_ORDER.map(bandRank)

    for (const [index, rank] of ranks.entries()) {
      expect(rank).toBe(index)
    }
  })

  it('groups the credentials together and the system rows together', () => {
    // The reason the rail is banded at all: these read as unrelated names
    // until something says they are the same kind of thing.
    expect(bandFor('providers')).toBe(bandFor('keys'))
    expect(bandFor('vault')).toBe(bandFor('config:workspace'))
    expect(bandFor('keybinds')).toBe(bandFor('about'))
    expect(bandFor('providers')).not.toBe(bandFor('about'))
  })

  it('names every band in every locale', () => {
    for (const [localeName, locale] of Object.entries(TRANSLATIONS)) {
      for (const key of BAND_ORDER) {
        if (key === '') {
          continue
        }

        expect(
          (locale.settings.bands as Record<string, string>)[key],
          `${localeName} is missing the "${key}" band heading`
        ).toBeTruthy()
      }
    }
  })

  it('bands every id it declares, and declares nothing twice', () => {
    expect(new Set(ids(SETTINGS_BANDS)).size).toBe(ids(SETTINGS_BANDS).length)

    for (const id of ids(SETTINGS_BANDS)) {
      expect(BAND_ORDER, `${id} is in a band BAND_ORDER does not list`).toContain(
        SETTINGS_BANDS[id] as (typeof BAND_ORDER)[number]
      )
    }
  })
})
