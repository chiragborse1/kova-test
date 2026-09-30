import { expect, test } from 'vitest'

import { electronDownloadTimeoutMs } from './prepare-packaging-tools.mjs'

const MINUTE = 60 * 1000

test('the Electron download ceiling outlasts app-builder-lib hard-coded 10 minute abort', () => {
  // The regression: app-builder-lib defaults `signal` to a 10 minute abort and
  // a slow link trips it mid-transfer, failing an install that was never broken.
  expect(electronDownloadTimeoutMs({})).toBeGreaterThan(10 * MINUTE)
})

test('KOVA_ELECTRON_DOWNLOAD_TIMEOUT_MINUTES raises the ceiling', () => {
  expect(electronDownloadTimeoutMs({ KOVA_ELECTRON_DOWNLOAD_TIMEOUT_MINUTES: '90' })).toBe(90 * MINUTE)
  // Fractions are useful for the test suite and for a genuinely slow link.
  expect(electronDownloadTimeoutMs({ KOVA_ELECTRON_DOWNLOAD_TIMEOUT_MINUTES: '0.5' })).toBe(30 * 1000)
})

test('a nonsensical override falls back to the default instead of aborting instantly', () => {
  // AbortSignal.timeout(0) fires on the next tick, which would break every build
  // on a host where the variable is set to a bad value by a wrapper script.
  for (const value of ['', '   ', 'abc', '0', '-5', 'NaN', 'Infinity']) {
    expect(electronDownloadTimeoutMs({ KOVA_ELECTRON_DOWNLOAD_TIMEOUT_MINUTES: value })).toBe(45 * MINUTE)
  }
})

test('the abort we pass overrides the dependency default rather than losing to it', () => {
  // electronGet.js builds its options as
  //   { signal: AbortSignal.timeout(10 * MINUTE), ...config.downloadOptions }
  // so a signal supplied through downloadOptions must win by identity. This
  // mirrors that exact spread order; if upstream ever reorders it, this fails.
  const ours = AbortSignal.timeout(electronDownloadTimeoutMs({}))
  const upstream = (config) => ({ signal: AbortSignal.timeout(10 * MINUTE), ...config.downloadOptions })
  expect(upstream({}).signal).not.toBe(ours)
  expect(upstream({ downloadOptions: { signal: ours } }).signal).toBe(ours)
})
