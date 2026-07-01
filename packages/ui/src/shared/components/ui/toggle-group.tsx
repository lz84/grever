import * as React from "react"
import { cn } from "@/lib/utils"

export type ToggleGroupItemProps = {
  value: string
  active?: boolean
  onClick?: (value: string) => void
  children: React.ReactNode
  className?: string
}

export function ToggleGroupItem({
  value,
  active,
  onClick,
  children,
  className,
}: ToggleGroupItemProps) {
  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
        "h-9 px-3 border",
        active
          ? "bg-primary text-primary-foreground border-primary"
          : "bg-background text-muted-foreground border-input hover:bg-accent hover:text-accent-foreground",
        className
      )}
      onClick={() => onClick?.(value)}
      aria-pressed={active}
    >
      {children}
    </button>
  )
}

export type ToggleGroupProps = {
  value: string
  onValueChange: (value: string) => void
  type?: "single"
  children: React.ReactNode
  className?: string
}

export function ToggleGroup({
  value,
  onValueChange,
  type = "single",
  children,
  className,
}: ToggleGroupProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-1 bg-muted rounded-lg p-1",
        className
      )}
      role="radiogroup"
    >
      {React.Children.map(children, child => {
        if (!React.isValidElement(child)) return null
        const itemValue = (child.props as any)?.value
        return React.cloneElement(child, {
          active: value === itemValue,
          onClick: () => onValueChange(itemValue),
        } as any)
      })}
    </div>
  )
}
