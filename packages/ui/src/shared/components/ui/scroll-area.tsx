import * as React from "react"
import { cn } from "@/lib/utils"
const ScrollArea = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { viewportRef?: React.Ref<HTMLDivElement> }>(({ className, children, viewportRef, ...props }, ref) => (
  <div ref={ref} className={cn("relative overflow-hidden", className)} {...props}>
    <div ref={viewportRef} className="h-full w-full rounded-[inherit] overflow-auto">
      {children}
    </div>
  </div>
))
ScrollArea.displayName = "ScrollArea"
const ScrollBar = ({ className, orientation = "vertical", ...props }: React.HTMLAttributes<HTMLDivElement> & { orientation?: "vertical" | "horizontal" }) => (
  <div
    className={cn(
      "flex touch-none select-none transition-colors",
      orientation === "vertical" && "h-full w-2.5 border-l border-l-transparent p-[1px]",
      orientation === "horizontal" && "h-2.5 flex-col border-t border-t-transparent p-[1px]",
      className
    )}
    {...props}
  >
    <div className={cn("flex-1 rounded-full bg-border", orientation === "vertical" && "")} />
  </div>
)
ScrollBar.displayName = "ScrollBar"
export { ScrollArea, ScrollBar }
