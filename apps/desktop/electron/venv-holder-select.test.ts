import assert from 'node:assert/strict'

import { test } from 'vitest'

import { hasWindowsPathPrefix, isExternalVenvHolder, isKovaOwnedVenvDaemon } from './venv-holder-select'

const SCRIPTS = 'C:\\Kova\\venv\\Scripts'

test('matches the hindsight daemon shim (exe under venv Scripts + hindsight cmdline)', () => {
  assert.equal(
    isKovaOwnedVenvDaemon(
      'C:\\Kova\\venv\\Scripts\\pythonw.exe',
      'C:\\Kova\\venv\\Scripts\\pythonw.exe -m hindsight_api.main --daemon --idle-timeout 300 --port 9177',
      SCRIPTS
    ),
    true
  )
})

test('Windows path prefix match is ordinal case-insensitive', () => {
  assert.equal(
    isKovaOwnedVenvDaemon(
      'c:\\kova\\venv\\scripts\\python.exe',
      'python.exe -m hindsight_api.main --daemon',
      'C:\\Kova\\venv\\Scripts'
    ),
    true
  )
})

test('excludes external venv holders that are not the hindsight daemon', () => {
  // a user terminal running the kova CLI from the venv — must NOT be killed
  assert.equal(isKovaOwnedVenvDaemon('C:\\Kova\\venv\\Scripts\\kova.exe', 'kova chat -q "hi"', SCRIPTS), false)
  // an unrelated python script using the venv interpreter
  assert.equal(
    isKovaOwnedVenvDaemon('C:\\Kova\\venv\\Scripts\\python.exe', 'python C:\\tools\\import.py', SCRIPTS),
    false
  )
})

test('excludes exes outside the venv even when the cmdline mentions hindsight', () => {
  assert.equal(
    isKovaOwnedVenvDaemon('C:\\Other\\pythonw.exe', 'pythonw -m hindsight_api.main --daemon', SCRIPTS),
    false
  )
})

test('prefix boundary: sibling dirs (ScriptsX) do not match', () => {
  assert.equal(hasWindowsPathPrefix('C:\\Kova\\venv\\ScriptsX\\python.exe', SCRIPTS), false)
  assert.equal(hasWindowsPathPrefix('C:\\Kova\\venv\\Scripts\\python.exe', SCRIPTS), true)
})

test('null/undefined fields never match', () => {
  assert.equal(isKovaOwnedVenvDaemon(null, 'x', SCRIPTS), false)
  assert.equal(isKovaOwnedVenvDaemon('C:\\Kova\\venv\\Scripts\\pythonw.exe', null, SCRIPTS), false)
  assert.equal(isKovaOwnedVenvDaemon(undefined, undefined, SCRIPTS), false)
})

// --- isExternalVenvHolder (#62311) ------------------------------------------

test('matches the autostart gateway shim (kova.exe under venv Scripts)', () => {
  assert.equal(
    isExternalVenvHolder(
      'C:\\Kova\\venv\\Scripts\\kova.exe',
      '"C:\\Kova\\venv\\Scripts\\kova.exe" gateway run --external-supervisor',
      SCRIPTS
    ),
    true
  )
})

test('matches the dashboard scheduled task (python -m kova_cli / -m kova)', () => {
  assert.equal(
    isExternalVenvHolder(
      'C:\\Kova\\venv\\Scripts\\python.exe',
      '"C:\\Kova\\venv\\Scripts\\python.exe" -m kova_cli.main dashboard',
      SCRIPTS
    ),
    true
  )
  assert.equal(isExternalVenvHolder('C:\\Kova\\venv\\Scripts\\pythonw.exe', 'pythonw.exe -m kova serve', SCRIPTS), true)
})

test('never matches an unrelated process that merely borrows the venv interpreter', () => {
  // a user's own script running on the venv python — NOT Kova, must NOT be killed
  assert.equal(
    isExternalVenvHolder('C:\\Kova\\venv\\Scripts\\python.exe', 'python C:\\tools\\import.py', SCRIPTS),
    false
  )
  // hindsight daemon is selected by isKovaOwnedVenvDaemon, not here
  assert.equal(
    isExternalVenvHolder('C:\\Kova\\venv\\Scripts\\pythonw.exe', 'pythonw -m hindsight_api.main --daemon', SCRIPTS),
    false
  )
})

test('never matches a process outside the venv, even with kova in the cmdline', () => {
  // an editor / shell whose command line mentions the install root (#62445 regression guard)
  assert.equal(
    isExternalVenvHolder('C:\\Windows\\System32\\cmd.exe', 'cmd /c cd C:\\Kova\\venv\\Scripts && dir', SCRIPTS),
    false
  )
  assert.equal(isExternalVenvHolder('C:\\Other\\kova.exe', 'kova gateway run', SCRIPTS), false)
})

test('sibling-dir and boundary safety for the external selector', () => {
  assert.equal(isExternalVenvHolder('C:\\Kova\\venv\\ScriptsX\\kova.exe', 'kova gateway run', SCRIPTS), false)
  assert.equal(isExternalVenvHolder(null, 'kova gateway run', SCRIPTS), false)
  assert.equal(isExternalVenvHolder('C:\\Kova\\venv\\Scripts\\kova.exe', null, SCRIPTS), false)
})
