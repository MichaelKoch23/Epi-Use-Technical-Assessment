import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon } from "lucide-react"
import { Spinner } from "@/components/ui/spinner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      position="top-center"
      duration={6000}
      closeButton
      icons={{
        success: (
          <CircleCheckIcon className="size-5 text-status-safe" />
        ),
        info: (
          <InfoIcon className="size-5 text-brand-teal" />
        ),
        warning: (
          <TriangleAlertIcon className="size-5 text-status-alert" />
        ),
        error: (
          <OctagonXIcon className="size-5 text-status-critical" />
        ),
        loading: (
          <Spinner className="size-5 text-brand-steel" />
        ),
      }}
      style={
        {
          "--normal-bg": "var(--card)",
          "--normal-text": "var(--foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
          "--width": "420px",
          "--toast-close-button-start": "auto",
          "--toast-close-button-end": "0",
          "--toast-close-button-transform": "translate(35%, -35%)",
        } as React.CSSProperties
      }
      toastOptions={{
        classNames: {
          toast: "cn-toast items-start! gap-3! p-4! shadow-lg!",
          title: "font-display text-sm! font-semibold! text-brand-primary",
          description: "text-xs! leading-snug! text-foreground!",
          icon: "mt-0.5",
          closeButton: "border-border! bg-card! text-muted-foreground!",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
