import { useEffect, useRef, useState } from 'react'

import type { DragKind } from '@/app/chat/hooks/use-file-drop-zone'
import { DROP_SHEET_BLUR_CLASS, DROP_SHEET_CLASS } from '@/components/ui/drop-affordance'
import { useI18n } from '@/i18n'
import { cn } from '@/lib/utils'

/**
 * Full-bleed affordance shown while files or a session are dragged over the chat
 * area. Always `pointer-events-none` so the drop lands on the real element
 * underneath and the drop-zone handler claims it — the overlay is purely visual.
 * The label names the outcome (attach files / link this chat); the last kind is
 * held through the fade-out so it doesn't blank.
 */
export function ChatDropOverlay({ kind }: { kind: DragKind }) {
  const { t } = useI18n()
  const lastKind = useRef<DragKind>(kind)

  if (kind) {
    lastKind.current = kind
  }

  const shown = kind ?? lastKind.current

  // Hold the sheet mounted for the length of the exit transition after `kind`
  // clears, so it eases away instead of vanishing between two frames. The
  // timer only ever runs on the way OUT; the way in paints immediately.
  // `exiting` holds the sheet in the tree for the length of the fade AFTER a
  // drag ends, so it eases away instead of disappearing between two frames.
  //
  // The first run has to be skipped. An effect that arms on mount would set
  // `exiting` true for a component that was rendered with `kind={null}` from
  // the start - putting the sheet straight back in the tree at rest, which is
  // the thing this change exists to remove. There is no transition to hold on
  // the opening render, so there is nothing to arm.
  const [exiting, setExiting] = useState(false)
  const wasDragging = useRef(false)
  // An EDGE DETECTOR, not a mirrored atom: only the truthy->falsy TRANSITION of
  // `kind` arms the fade, and reading `kind` here would also arm on the
  // opening render - the bug this effect exists to avoid.
  // eslint-disable-next-line no-restricted-syntax -- edge detector, not a mirror
  useEffect(() => {
    if (kind) {
      wasDragging.current = true
      setExiting(false)

      return
    }

    if (!wasDragging.current) {
      return
    }

    wasDragging.current = false
    setExiting(true)
    const timer = window.setTimeout(() => setExiting(false), 180)

    return () => window.clearTimeout(timer)
  }, [kind])

  // The sheet carries a `backdrop-filter: blur(2px)` over the FULL window
  // (measured: 1773x1052). It used to stay mounted forever and be hidden with
  // `opacity-0`, which is correct on screen - a pixel diff with and without it
  // is identical, because opacity-0 suppresses the filter - but it still left a
  // window-sized blur layer in the tree on every chat surface for the whole
  // session, holding a compositing layer alive that the compositor has to
  // reason about whenever anything under it repaints. The transcript is
  // virtualised and repaints constantly.
  //
  // Mount only while a drag is live. `lastKind` is what keeps the LABEL alive
  // through the exit fade, so the guard is on `kind` alone - testing `shown`
  // here would never be falsy (the ref persists), and the sheet would stay
  // mounted forever, which is the thing being fixed.
  if (!kind && !exiting) {
    return null
  }

  return (
    <div
      aria-hidden
      className={cn(
        'pointer-events-none absolute inset-0 z-40 flex items-center justify-center transition-opacity fast ease-out',
        kind ? 'opacity-100' : 'opacity-0'
      )}
      data-slot="chat-drop-overlay"
    >
      <div
        className={cn(
          DROP_SHEET_CLASS,
          DROP_SHEET_BLUR_CLASS,
          'absolute inset-2 border-[color-mix(in_srgb,var(--dt-composer-ring)_55%,transparent)] bg-[color-mix(in_srgb,var(--dt-card)_55%,transparent)]'
        )}
      />
      {shown && (
        <span className="relative text-[11px] font-medium uppercase tracking-wide text-foreground">
          {shown === 'session' ? t.composer.dropSession : t.composer.dropFiles}
        </span>
      )}
    </div>
  )
}
