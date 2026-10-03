/**
 * Which band each Settings rail destination belongs to, and in what order the
 * bands read. Extracted from the component so the rule can be tested without a
 * DOM - and so the two halves cannot drift apart.
 *
 * Why this exists: the rail listed 22 destinations in one flat column. It
 * fits (677px of a 925px window, no scrollbar), so the problem was never
 * space. A flat list that long asks the reader to already know which of 22
 * names belongs to the thing they are after - `Providers`, `Gateways`,
 * `Tools & Keys` and `Passwords & Logins` are all credentials, `Advanced`,
 * `Keyboard Shortcuts` and `About` are all system, and nothing on screen said
 * so.
 *
 * OpenClaw groups the same kind of rail into labelled bands
 * (`SETTINGS_NAVIGATION_GROUPS` in its `ui/src/app-navigation.ts`), and its
 * settings design doc gives the rule this follows: "Sections are typography,
 * not chrome. Grouping comes from whitespace + a small uppercase heading -
 * never a card header."
 */

/**
 * Band key by rail row id. The empty string is the FIRST band and is
 * deliberately UNLABELLED: Model, Chat and Appearance are what a person opens
 * Settings for, and a heading above them would label the obvious.
 *
 * Ids not listed here are left unbanded rather than guessed into a group - an
 * unbanded row is visible in review, a wrongly-banded one is not.
 */
export const SETTINGS_BANDS: Readonly<Record<string, string>> = {
  'config:model': '',
  'config:chat': '',
  'config:appearance': '',
  'config:workspace': 'bandDevice',
  'config:browser': 'bandDevice',
  vault: 'bandDevice',
  'config:safety': 'bandSecurity',
  'config:memory': 'bandSecurity',
  notifications: 'bandSecurity',
  'config:voice': 'bandAgents',
  providers: 'bandAgents',
  keys: 'bandAgents',
  gateway: 'bandConnections',
  billing: 'bandAccount',
  keybinds: 'bandSystem',
  'config:advanced': 'bandSystem',
  sessions: 'bandSystem',
  about: 'bandSystem'
}

/**
 * Band order on the rail. The empty string sorts first; the rest read in the
 * order a person configures Kova - this machine, then what it talks to, then
 * what runs, then what it may touch, then who you are, then the machine
 * itself.
 */
export const BAND_ORDER = [
  '',
  'bandDevice',
  'bandConnections',
  'bandAgents',
  'bandSecurity',
  'bandAccount',
  'bandSystem'
] as const

export type SettingsBand = (typeof BAND_ORDER)[number]

/**
 * The band key for a row, or `null` when the row is in no band.
 *
 * The first band is the EMPTY STRING, so this tests for `null` explicitly
 * rather than for truthiness: `key ? ...` treats '' as absent and would send
 * the whole first band to the end of the rail.
 */
export function bandFor(id: string): string | null {
  return Object.prototype.hasOwnProperty.call(SETTINGS_BANDS, id) ? SETTINGS_BANDS[id] : null
}

/**
 * Sort position for a band key. An unbanded row sorts LAST rather than at -1:
 * it still has to be reachable, and dropping it into the middle of a band it
 * does not belong to is the silent mis-grouping the table exists to prevent.
 */
export function bandRank(key: string | null): number {
  return key === null ? BAND_ORDER.length : Math.max(0, BAND_ORDER.indexOf(key as SettingsBand))
}
