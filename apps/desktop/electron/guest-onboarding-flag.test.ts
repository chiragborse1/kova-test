import assert from 'node:assert/strict'

import { test } from 'vitest'

import { desktopBackendSpawnEnv, guestOnboardingEnabled, skipIntroEnabled } from './guest-onboarding'
import { buildSpawnCommand } from './remote-lifecycle'

test('skipIntroEnabled: exactly "1" in env or --skip-intro on argv skips the first-run film', () => {
  assert.equal(skipIntroEnabled([], { KOVA_SKIP_INTRO: '1' }), true)
  assert.equal(skipIntroEnabled(['electron', '.', '--skip-intro'], {}), true)

  assert.equal(skipIntroEnabled([], {}), false)
  assert.equal(skipIntroEnabled([], { KOVA_SKIP_INTRO: 'true' }), false)
})

test('guestOnboardingEnabled: exactly "1" in env or --guest-onboarding on argv turns the free tier on', () => {
  assert.equal(guestOnboardingEnabled([], { KOVA_GUEST_ONBOARDING: '1' }), true)
  assert.equal(guestOnboardingEnabled(['electron', '.', '--guest-onboarding'], {}), true)

  assert.equal(guestOnboardingEnabled([], {}), false)
  assert.equal(guestOnboardingEnabled([], { KOVA_GUEST_ONBOARDING: 'true' }), false)
  assert.equal(guestOnboardingEnabled([], { KOVA_GUEST_ONBOARDING: '0' }), false)
  assert.equal(guestOnboardingEnabled(['electron', '.', '--local'], { KOVA_GUEST_ONBOARDING: '' }), false)
})

test('desktopBackendSpawnEnv stamps the launch decision last and never lets an inherited value leak', () => {
  const base = {
    KOVA_HOME: '/tmp/home',
    KOVA_DESKTOP: '1',
    KOVA_GUEST_ONBOARDING: '1',
    PATH: '/usr/bin'
  }

  const on = desktopBackendSpawnEnv({ ...base, KOVA_GUEST_ONBOARDING: '0' }, true)
  assert.equal(on.KOVA_GUEST_ONBOARDING, '1')

  const off = desktopBackendSpawnEnv(base, false)
  assert.equal(off.KOVA_GUEST_ONBOARDING, '0', 'a stray inherited "1" must not turn the free tier on')

  for (const env of [on, off]) {
    assert.equal(env.KOVA_HOME, base.KOVA_HOME)
    assert.equal(env.KOVA_DESKTOP, base.KOVA_DESKTOP)
    assert.equal(env.PATH, base.PATH)
  }
})

test('remote SSH spawn command carries KOVA_GUEST_ONBOARDING=1 only when the launch decided on', () => {
  const on = buildSpawnCommand('/x/kova', 'work', { logPath: '~/.kova/log', guestOnboarding: true })
  assert.match(on, /exec env KOVA_DESKTOP=1 KOVA_GUEST_ONBOARDING=1 /)

  const off = buildSpawnCommand('/x/kova', 'work', { logPath: '~/.kova/log', guestOnboarding: false })
  assert.match(off, /exec env KOVA_DESKTOP=1 /)
  assert.doesNotMatch(off, /KOVA_GUEST_ONBOARDING/)

  const unset = buildSpawnCommand('/x/kova', 'work', { logPath: '~/.kova/log' })
  assert.doesNotMatch(unset, /KOVA_GUEST_ONBOARDING/)
})
