import { BarChart3, CircleUserRound, History, LogOutIcon, Network, Search, Table2, Upload } from 'lucide-react'
import { NavLink, Outlet } from 'react-router'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/features/auth/useAuth'

// Mirrors the "topbar-demo" / "nav-demo" patterns in the brand style
// guide (docs/brand_style_guide.html, §Navigation): a primary-colour
// topbar with the wordmark and utility actions, and a pill-shaped nav
// bar below it whose active item is driven by aria-current="page" —
// which NavLink sets automatically.
const NAV_ITEMS = [
  { to: '/chart', label: 'Org chart', icon: Network },
  { to: '/employees', label: 'Employees', icon: Table2 },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/import', label: 'Import', icon: Upload },
]

export function AppShell() {
  const { principal, logout } = useAuth()

  return (
    <div className="min-h-svh bg-background">
      <header className="flex h-14 items-center justify-between bg-brand-primary px-4 text-white print:hidden">
        <span className="font-display text-lg font-extrabold tracking-wide">EHM</span>
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label="Search"
            className="grid size-9 place-items-center rounded-sm hover:bg-white/10"
          >
            <Search className="size-4" />
          </button>
          <button
            type="button"
            aria-label="Change history"
            className="grid size-9 place-items-center rounded-sm hover:bg-white/10"
          >
            <History className="size-4" />
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger
              aria-label="Account"
              render={
                <button
                  type="button"
                  className="grid size-8 place-items-center rounded-full bg-brand-steel text-brand-primary"
                />
              }
            >
              <CircleUserRound className="size-5" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {principal && (
                <>
                  <DropdownMenuGroup>
                    <DropdownMenuLabel className="flex flex-col gap-0.5">
                      <span className="font-medium text-foreground">{principal.email}</span>
                      <span className="text-xs font-normal text-muted-foreground capitalize">
                        {principal.role.replace('_', ' ')}
                      </span>
                    </DropdownMenuLabel>
                  </DropdownMenuGroup>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem onClick={logout}>
                <LogOutIcon /> Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </header>

      <div className="p-4">
        <nav
          aria-label="Primary"
          className="mb-4 flex flex-wrap gap-1 rounded-md border border-border bg-card p-1 print:hidden"
        >
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className="inline-flex items-center gap-2 rounded-sm px-4 py-2 text-sm font-medium text-brand-mid no-underline aria-[current=page]:bg-brand-primary aria-[current=page]:text-white"
            >
              <Icon className="size-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <main>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
