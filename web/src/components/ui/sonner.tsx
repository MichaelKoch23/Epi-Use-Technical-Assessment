import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"
import { CircleCheckIcon, InfoIcon, TriangleAlertIcon, OctagonXIcon } from "lucide-react"
import { Spinner } from "@/components/ui/spinner"

/**
 * Top-centre, wide and slow to leave: a confirmation nobody notices is the same
 * as no confirmation at all. Status is carried by the icon's shape and colour,
 * so it is never colour alone. `!` is needed on the utilities because sonner's
 * own unlayered CSS would otherwise win over Tailwind's utility layer.
 */
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
          // Sonner anchors the close button to the top-left corner by default.
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
