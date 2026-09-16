import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { LogIn } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'
import { setTokens } from '@/lib/auth'
import { meQueryKey } from './useAuth'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()

  const loginMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/auth/login', {
        body: { email, password },
      })
      if (error) throw error
      return data
    },
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
      void queryClient.invalidateQueries({ queryKey: meQueryKey })
      const redirectTo = (location.state as { from?: string } | null)?.from ?? '/chart'
      navigate(redirectTo, { replace: true })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Incorrect email or password'))
    },
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    loginMutation.mutate()
  }

  return (
    <div className="grid min-h-svh bg-surface-bg lg:grid-cols-[minmax(0,1fr)_minmax(0,32rem)]">
      {/* Brand panel - the style guide's hero: primary fill, lineage
          motif, overline + extrabold display heading. Collapses to a
          compact band above the form on small screens. */}
      <section className="relative flex overflow-hidden bg-brand-primary text-white">
        <LineageMotif />
        <div className="relative flex w-full flex-col justify-between gap-8 p-6 lg:p-12">
          <span className="font-display text-lg font-extrabold tracking-wide">EHM</span>
          <div className="max-w-[46ch]">
            <span className="font-display text-sm font-semibold tracking-widest text-brand-light uppercase">
              EPI-USE Africa
            </span>
            <h1 className="mt-2 font-display text-3xl leading-[0.95] font-extrabold tracking-tight lg:text-5xl">
              Employee Hierarchy Management System
            </h1>
            <p className="mt-4 hidden text-lg leading-snug text-white/80 sm:block">
              One organisation, one reporting structure, one set of rules for how it changes.
            </p>
          </div>
          <span aria-hidden="true" className="hidden lg:block" />
        </div>
      </section>

      <main className="flex items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-sm rounded-md border border-border bg-card p-6 shadow-sm">
          <h2 className="font-display text-2xl font-bold text-brand-primary">Sign in</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Use the email address and password your administrator issued.
          </p>

          <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-5">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email" className="font-semibold text-brand-primary">
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="h-11 rounded-sm px-3 text-base md:text-base"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password" className="font-semibold text-brand-primary">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="h-11 rounded-sm px-3 text-base md:text-base"
              />
            </div>
            <Button
              type="submit"
              disabled={loginMutation.isPending}
              className="mt-1 h-11 rounded-sm font-semibold tracking-[0.5px]"
            >
              {loginMutation.isPending ? (
                'Signing in…'
              ) : (
                <>
                  <LogIn /> Sign in
                </>
              )}
            </Button>
          </form>
        </div>
      </main>
    </div>
  )
}

// The branching "lineage" illustration from the style guide hero
// (docs/brand_style_guide.html, #top), anchored to the right edge.
const LINEAGE_PATHS: [string, number][] = [
  ['M760,170 H820', 1.2],
  ['M820,170 V70 H880', 1.2],
  ['M820,170 V270 H880', 1.2],
  ['M880,70 V30 H940', 1],
  ['M880,70 V110 H940', 1],
  ['M880,270 V230 H940', 1],
  ['M880,270 V310 H940', 1],
  ['M940,110 V90 H1010', 0.8],
  ['M940,110 V140 H1010', 0.8],
  ['M940,230 V200 H1010', 0.8],
  ['M940,230 V260 H1010', 0.8],
  ['M1010,140 V130 H1090', 0.7],
  ['M1010,140 V165 H1090', 0.7],
  ['M1010,200 V185 H1090', 0.7],
]
const LINEAGE_NODES: [number, number, number][] = [
  [760, 170, 7],
  [880, 70, 5],
  [880, 270, 5],
  [940, 30, 4],
  [940, 110, 4],
  [940, 230, 4],
  [940, 310, 4],
  [1010, 90, 3],
  [1010, 140, 3],
  [1010, 200, 3],
  [1010, 260, 3],
  [1090, 130, 2.5],
  [1090, 165, 2.5],
  [1090, 185, 2.5],
]

function LineageMotif() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 1200 340"
      preserveAspectRatio="xMaxYMid meet"
      className="absolute inset-0 size-full opacity-55"
    >
      <g opacity="0.5" className="fill-brand-light stroke-brand-light">
        {LINEAGE_PATHS.map(([d, width]) => (
          <path key={d} d={d} fill="none" strokeWidth={width} strokeLinecap="round" />
        ))}
        {LINEAGE_NODES.map(([cx, cy, r]) => (
          <circle key={`${cx}-${cy}`} cx={cx} cy={cy} r={r} stroke="none" />
        ))}
      </g>
    </svg>
  )
}
