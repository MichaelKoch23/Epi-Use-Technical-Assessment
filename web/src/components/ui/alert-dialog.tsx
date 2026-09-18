"use client"

import * as React from "react"
import { AlertDialog as AlertDialogPrimitive } from "@base-ui/react/alert-dialog"
import { XIcon } from "lucide-react"
import { cn } from "cn"

import { Button } from "@/components/ui/button"

function AlertDialog({ ...props }: AlertDialogPrimitive.Root.Props) {
  return <AlertDialogPrimitive.Root data-slot="alert-dialog" {...props} />
}

function AlertDialogTrigger({ ...props }: AlertDialogPrimitive.Trigger.Props) {
  return (
    <AlertDialogPrimitive.Trigger data-slot="alert-dialog-trigger" {...props} />
  )
}

function AlertDialogPortal({ ...props }: AlertDialogPrimitive.Portal.Props) {
  return (
    <AlertDialogPrimitive.Portal data-slot="alert-dialog-portal" {...props} />
  )
}

function AlertDialogOverlay({
  className,
  ...props
}: AlertDialogPrimitive.Backdrop.Props) {
  return (
    <AlertDialogPrimitive.Backdrop
      data-slot="alert-dialog-overlay"
      className={cn(
        "fixed inset-0 isolate z-50 bg-black/80 data-open:animate-in data-open:fade-in-0 data-open:duration-[400ms] data-open:ease-[cubic-bezier(0,0,0.2,1)] data-closed:animate-out data-closed:fade-out-0 data-closed:duration-[250ms] data-closed:ease-[cubic-bezier(0.4,0,1,1)] motion-reduce:animate-none",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogContent({
  className,
  ...props
}: AlertDialogPrimitive.Popup.Props) {
  return (
    <AlertDialogPortal>
      <AlertDialogOverlay />
      <AlertDialogPrimitive.Popup
        data-slot="alert-dialog-content"
        className={cn(
          "fixed top-1/2 left-1/2 z-50 flex max-h-[85vh] w-[90%] max-w-[420px] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-xl bg-card text-card-foreground shadow-[0_4px_12px_rgba(0,0,0,0.12)] outline-none data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-open:duration-[400ms] data-open:ease-[cubic-bezier(0,0,0.2,1)] data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95 data-closed:duration-[250ms] data-closed:ease-[cubic-bezier(0.4,0,1,1)] motion-reduce:animate-none",
          className
        )}
        {...props}
      />
    </AlertDialogPortal>
  )
}

function AlertDialogHeader({
  className,
  children,
  showCloseButton = true,
  ...props
}: React.ComponentProps<"div"> & { showCloseButton?: boolean }) {
  return (
    <div
      data-slot="alert-dialog-header"
      className={cn(
        "flex shrink-0 items-start justify-between gap-3 border-b border-border px-6 pt-5 pb-4",
        className
      )}
      {...props}
    >
      <div className="flex flex-col gap-1.5">{children}</div>
      {showCloseButton && (
        <AlertDialogPrimitive.Close
          data-slot="alert-dialog-close"
          aria-label="Cancel, close dialog"
          render={
            <Button
              variant="ghost"
              className="-mt-3 -mr-3 size-11 shrink-0 p-0 text-muted-foreground has-[>svg]:p-0"
            />
          }
        >
          <XIcon className="size-5" />
        </AlertDialogPrimitive.Close>
      )}
    </div>
  )
}

function AlertDialogBody({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-body"
      className={cn(
        "flex flex-col gap-4 overflow-y-auto px-6 py-5 text-base leading-relaxed text-foreground",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogFooter({
  className,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-footer"
      className={cn(
        "flex shrink-0 flex-col-reverse gap-3 border-t border-border px-6 pt-4 pb-5 sm:flex-row sm:justify-end",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogTitle({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Title>) {
  return (
    <AlertDialogPrimitive.Title
      data-slot="alert-dialog-title"
      className={cn(
        "font-heading text-xl leading-[1.15] font-bold text-brand-primary",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogDescription({
  className,
  ...props
}: React.ComponentProps<typeof AlertDialogPrimitive.Description>) {
  return (
    <AlertDialogPrimitive.Description
      data-slot="alert-dialog-description"
      className={cn(
        "text-base leading-relaxed text-foreground *:[a]:underline *:[a]:underline-offset-3",
        className
      )}
      {...props}
    />
  )
}

function AlertDialogAction({
  className,
  ...props
}: React.ComponentProps<typeof Button>) {
  return (
    <Button
      data-slot="alert-dialog-action"
      className={cn(className)}
      {...props}
    />
  )
}

function AlertDialogCancel({
  className,
  variant = "outline",
  size = "default",
  ...props
}: AlertDialogPrimitive.Close.Props &
  Pick<React.ComponentProps<typeof Button>, "variant" | "size">) {
  return (
    <AlertDialogPrimitive.Close
      data-slot="alert-dialog-cancel"
      className={cn(className)}
      render={<Button variant={variant} size={size} />}
      {...props}
    />
  )
}

export {
  AlertDialog,
  AlertDialogAction,
  AlertDialogBody,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  AlertDialogPortal,
  AlertDialogTitle,
  AlertDialogTrigger,
}
