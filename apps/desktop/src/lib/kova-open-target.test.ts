import { describe, expect, it } from 'vitest'

import {
  normalizeKovaOpenString,
  pathFromKovaDeepLink,
  pathFromOpenDeepLink,
  resolveKovaOpenPath
} from './kova-open-target'

describe('normalizeKovaOpenString', () => {
  it('accepts hash-router paths and strips a leading hash', () => {
    expect(normalizeKovaOpenString('/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeKovaOpenString('#/index-network/intent/1')).toBe('/index-network/intent/1')
  })

  it('maps plugin-scoped kova:// deep links to the same path', () => {
    expect(normalizeKovaOpenString('kova://index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeKovaOpenString('kova://index-network/intent/1?focus=true')).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('maps kova://open/… deep links by stripping the open host', () => {
    expect(normalizeKovaOpenString('kova://open/index-network/intent/1')).toBe('/index-network/intent/1')
    expect(normalizeKovaOpenString('kova://open/settings/plugins')).toBe('/settings/plugins')
  })

  it('rejects reserved kova kinds and unsafe paths', () => {
    expect(normalizeKovaOpenString('kova://blueprint/morning-brief')).toBeNull()
    expect(normalizeKovaOpenString('kova://plugin/install')).toBeNull()
    expect(normalizeKovaOpenString('https://example.com/x')).toBeNull()
    expect(normalizeKovaOpenString('/../etc/passwd')).toBeNull()
    expect(normalizeKovaOpenString('index-network')).toBeNull()
  })
})

describe('resolveKovaOpenPath', () => {
  it('merges structured path + params', () => {
    expect(resolveKovaOpenPath({ path: '/index-network/intent/1', params: { focus: 'true' } })).toBe(
      '/index-network/intent/1?focus=true'
    )
  })

  it('resolves href the same as a bare string', () => {
    expect(resolveKovaOpenPath({ href: 'kova://index-network/intent/1' })).toBe('/index-network/intent/1')
  })
})

describe('pathFromKovaDeepLink', () => {
  it('builds the navigate path from a plugin-scoped deep-link payload', () => {
    expect(pathFromKovaDeepLink('index-network', 'intent/1')).toBe('/index-network/intent/1')
  })

  it('builds the navigate path from kova://open/… payloads', () => {
    expect(pathFromOpenDeepLink('index-network/intent/1')).toBe('/index-network/intent/1')
    expect(pathFromKovaDeepLink('open', 'agent/42')).toBe('/agent/42')
  })

  it('ignores reserved kinds', () => {
    expect(pathFromKovaDeepLink('blueprint', 'morning-brief')).toBeNull()
    expect(pathFromKovaDeepLink('plugin', 'install')).toBeNull()
    expect(pathFromKovaDeepLink('skill', 'install')).toBeNull()
  })
})
