import { describe, expect, it, vi } from 'vitest'

import { terminalParityHints } from '../lib/terminalParity.js'

describe('terminalParityHints', () => {
  it('warns for Apple Terminal and SSH/tmux sessions', async () => {
    const hints = await terminalParityHints({
      TERM_PROGRAM: 'Apple_Terminal',
      TERM_SESSION_ID: 'w0t0p0:123',
      SSH_CONNECTION: '1',
      TMUX: '/tmp/tmux-1/default,1,0'
    } as NodeJS.ProcessEnv)

    expect(hints.map(h => h.key)).toEqual(expect.arrayContaining(['apple-terminal', 'remote', 'tmux']))
  })

  it('suggests IDE setup only for VS Code-family terminals that still need bindings', async () => {
    const readFile = vi.fn().mockRejectedValue(Object.assign(new Error('missing'), { code: 'ENOENT' }))

    // platform is stated rather than inherited: on win32 the VS Code config dir
    // comes from APPDATA, so the caller's homeDir is ignored and the hint
    // disappears. That made this pass on the Linux runner and fail on Windows.
    const hints = await terminalParityHints({ TERM_PROGRAM: 'vscode' } as NodeJS.ProcessEnv, {
      fileOps: { readFile },
      homeDir: '/tmp/fake-home',
      platform: 'darwin'
    })

    expect(hints.some(h => h.key === 'ide-setup')).toBe(true)
  })
})
