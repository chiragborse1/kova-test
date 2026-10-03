// The drop sheet carries a window-sized `backdrop-filter: blur(2px)`. It used to
// stay mounted for the whole session and be hidden with `opacity-0`, which is
// invisible on screen (a pixel diff with and without it is identical) but kept a
// full-window compositing layer alive on every chat surface while the
// virtualised transcript repainted underneath it.
//
// What needs pinning: the sheet is NOT in the tree at rest, it IS while a drag
// is live, and the label survives the exit fade rather than blanking.
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ChatDropOverlay } from './chat-drop-overlay'

const overlay = () => document.querySelector('[data-slot="chat-drop-overlay"]')

afterEach(() => {
  cleanup()
})

describe('ChatDropOverlay', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  it('renders nothing at rest, so no window-sized blur layer is mounted', () => {
    render(<ChatDropOverlay kind={null} />)

    expect(overlay()).toBeNull()
  })

  it('mounts the sheet while a drag is live', () => {
    render(<ChatDropOverlay kind="files" />)

    expect(overlay()).not.toBeNull()
  })

  it('holds the sheet through the exit fade so the label does not blank', () => {
    const { rerender } = render(<ChatDropOverlay kind="files" />)
    expect(screen.getByText(/drop/i)).toBeTruthy()

    rerender(<ChatDropOverlay kind={null} />)
    // still mounted, mid-fade, and still labelled
    expect(overlay()).not.toBeNull()
    expect(screen.getByText(/drop/i)).toBeTruthy()

    // once the fade window closes, the layer is gone. act() because the
    // teardown is a timer-driven state update, and without it React has not
    // flushed the re-render that removes the node when we assert.
    act(() => {
      vi.advanceTimersByTime(200)
    })
    expect(overlay()).toBeNull()
  })

  it('re-arms when a second drag follows, rather than latching closed', () => {
    const { rerender } = render(<ChatDropOverlay kind="files" />)
    rerender(<ChatDropOverlay kind={null} />)
    act(() => {
      vi.advanceTimersByTime(200)
    })
    expect(overlay()).toBeNull()

    rerender(<ChatDropOverlay kind="session" />)
    expect(overlay()).not.toBeNull()
  })
})
