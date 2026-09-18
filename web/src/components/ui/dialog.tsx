import * as React from "react"
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog"
import { cn } from "cn"

import { Button } from "@/components/ui/button"
import { XIcon } from "lucide-react"

function Dialog({ ...props }: DialogPrimitive.Root.Props) {
  return <DialogPrimitive.Root data-slot="dialog" {...props} />
}

function DialogTrigger({ ...props }: DialogPrimitive.Trigger.Props) {
  return <DialogPrimitive.Trigger data-slot="dialog-trigger" {...props} />
}

function DialogPortal({ ...props }: DialogPrimitive.Portal.Props) {
  return <DialogPrimitive.Portal data-slot="dialog-portal" {...props} />
}

function DialogClose({ ...props }: DialogPrimitive.Close.Props) {
  return <DialogPrimitive.Close data-slot="dialog-close" {...props} />
}

function DialogOverlay({
  className,
  ...props
}: DialogPrimitive.Backdrop.Props) {
  return (
    <DialogPrimitive.Backdrop
      data-slot="dialog-overlay"
      className={cn(
        "fixed inset-0 isolate z-50 bg-black/80 data-open:animate-in data-open:fade-in-0 data-open:duration-[400ms] data-open:ease-[cubic-bezier(0,0,0.2,1)] data-closed:animate-out data-closed:fade-out-0 data-closed:duration-[250ms] data-closed:ease-[cubic-bezier(0.4,0,1,1)] motion-reduce:animate-none",
        className
      )}
      {...props}
    />
  )
}

function DialogContent({
  className,
  children,
  ...props
}: DialogPrimitive.Popup.Props) {
  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Popup
        data-slot="dialog-content"
        className={cn(
          "fixed top-1/2 left-1/2 z-50 flex max-h-[85vh] w-[90%] max-w-[420px] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-xl bg-card text-card-foreground shadow-[0_4px_12px_rgba(0,0,0,0.12)] outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-open:duration-[400ms] data-open:ease-[cubic-bezier(0,0,0.2,1)] data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95 data-closed:duration-[250ms] data-closed:ease-[cubic-bezier(0.4,0,1,1)] motion-reduce:animate-none",
          className
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Popup>
    </DialogPortal>
  )
}

function DialogHeader({
  className,
  children,
  showCloseButton = true,
  ...props
}: React.ComponentProps<"div"> & { showCloseButton?: boolean }) {
  return (
    <div
      data-slot="dialog-header"
      className={cn(
        "flex shrink-0 items-start justify-between gap-3 border-b border-border px-6 pt-5 pb-4",
        className
      )}
      {...props}
    >
      <div className="flex flex-col gap-1.5">{children}</div>
      {showCloseButton && (
        <DialogPrimitive.Close
          data-slot="dialog-close"
          aria-label="Close dialog"
          render={
            <Button
              variant="ghost"
              className="-mt-3 -mr-3 size-11 shrink-0 p-0 text-muted-foreground has-[>svg]:p-0"
            />
          }
        >
          <XIcon className="size-5" />
        </DialogPrimitive.Close>
      )}
    </div>
  )
}

/** The Modal spec's body: --sp-5/--sp-6 padding, base text, relaxed leading. */
function DialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-body"
      className={cn(
        "flex flex-col gap-4 overflow-y-auto px-6 py-5 text-base leading-relaxed text-foreground",
        className
      )}
      {...props}
    />
  )
}

function DialogFooter({
  className,
  showCloseButton = false,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  showCloseButton?: boolean
}) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn(
        "flex shrink-0 flex-col-reverse gap-3 border-t border-border px-6 pt-4 pb-5 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    >
      {children}
      {showCloseButton && (
        <DialogPrimitive.Close render={<Button variant="outline" />}>
          Close
        </DialogPrimitive.Close>
      )}
    </div>
  )
}

function DialogTitle({ className, ...props }: DialogPrimitive.Title.Props) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn(
        "font-heading text-xl leading-[1.15] font-bold text-brand-primary",
        className
      )}
      {...props}
    />
  )
}

function DialogDescription({
  className,
  ...props
}: DialogPrimitive.Description.Props) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn(
        "text-base leading-relaxed text-foreground *:[a]:underline *:[a]:underline-offset-3",
        className
      )}
      {...props}
    />
  )
}

export {
  Dialog,
  DialogBody,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
}
