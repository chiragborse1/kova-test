import type * as React from 'react'

import { cn } from '@/lib/utils'

interface SidebarPanelLabelProps extends React.ComponentProps<'span'> {
  dotClassName?: string
  meta?: React.ReactNode
}

/**
 * A panel section label: PINNED, SESSIONS, and the right rail's equivalents.
 *
 * These were `text-(--theme-primary)` - full-strength accent violet at 10px
 * semibold. That put the LOUDEST colour in the sidebar on a passive label, so
 * "PINNED" and "SESSIONS" outshouted the five nav rows that are actual
 * destinations, and the accent got spent on decoration instead of on state.
 * It also spent colour on a SECOND plane after the palette fix, which is the
 * habit that fix was meant to break.
 *
 * A label is structure, not state: it wears the muted foreground and lets the
 * accent mean one thing (selection, focus, primary action). The dot carries a
 * 4px dither mark rather than an 8px solid block, so the label reads as a
 * quiet divider instead of a chip.
 */
export function SidebarPanelLabel({ children, className, dotClassName, meta, ...props }: SidebarPanelLabelProps) {
  return (
    <span
      className={cn(
        'flex min-w-0 items-center gap-1.5 pl-2 text-xs font-semibold uppercase tracking-caps text-(--ui-text-tertiary)',
        className
      )}
      {...props}
    >
      <span aria-hidden="true" className={cn('dither inline-block size-1 shrink-0 rounded-xs', dotClassName)} />
      <span className="min-w-0 truncate leading-none">{children}</span>
      {meta && (
        <span className="shrink-0 text-sm font-medium tracking-normal text-(--ui-text-quaternary)">
          {meta}
        </span>
      )}
    </span>
  )
}
