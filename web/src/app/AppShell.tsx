import { useEffect, useState } from 'react'
import { BarChart3, History, LogOutIcon, Network, Search, Table2, Upload, UserRoundIcon } from 'lucide-react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import ehmMark from '@/assets/ehm-mark.png'
import { EmployeeAvatar } from '@/components/employee-avatar'
import { useAuth } from '@/features/auth/useAuth'
import { CommandPalette } from '@/features/search/CommandPalette'
import { nameFromEmail } from '@/lib/emailName'

// Mirrors the "topbar-demo" / "nav-demo" patterns in the brand style
// guide (docs/brand_style_guide.html, §Navigation): a primary-colour
// topbar with the wordmark and utility actions, and a pill-shaped nav
// bar below it whose active item is driven by aria-current="page" -
// which NavLink sets automatically.
const NAV_ITEMS = [
  { to: '/chart', label: 'Org chart', icon: Network },
  { to: '/employees', label: 'Employees', icon: Table2 },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/import', label: 'Import', icon: Upload },
]

export function AppShell() {
  const { principal, logout } = useAuth()
  const [paletteOpen, setPaletteOpen] = useState(false)
  const navigate = useNavigate()
  const accountName = principal ? nameFromEmail(principal.email) : null

  // Cmd/Ctrl+K opens the command palette from anywhere in the app, the
  // conventional shortcut for one - the topbar button is the discoverable
  // path, this is the fast one.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key.toLowerCase() === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault()
        setPaletteOpen((open) => !open)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <div className="min-h-svh bg-background">
      <header className="flex h-14 items-center justify-between bg-brand-primary px-4 text-white print:hidden">
        <Link to="/chart" className="flex items-center gap-2">
          {/* White tile: the mark's navy root node would vanish on the navy bar. */}
          <span className="grid size-9 place-items-center rounded-sm bg-white p-1">
            <img src={ehmMark} alt="" className="size-full" />
          </span>
          <span className="font-display text-lg font-extrabold tracking-wide">EHM</span>
        </Link>
        <div className="flex items-center gap-3">
          <button
            type="button"
            aria-label="Search"
            onClick={() => setPaletteOpen(true)}
            className="grid size-9 place-items-center rounded-sm hover:bg-white/10"
          >
            <Search className="size-4" />
          </button>
          <Link
            to="/history"
            aria-label="Change history"
            className="grid size-9 place-items-center rounded-sm hover:bg-white/10"
          >
            <History className="size-4" />
          </Link>
          <DropdownMenu>
            <DropdownMenuTrigger
              aria-label="Account"
              render={
                <button
                  type="button"
                  className="grid size-9 place-items-center rounded-sm hover:bg-white/10 data-popup-open:bg-white/10"
                />
              }
            >
              {/* Same translucent treatment as the other topbar actions, so the
                  avatar reads as part of the bar rather than a pasted-on badge. */}
              {principal && accountName ? (
                <EmployeeAvatar
                  avatarUrl={principal.avatar_url}
                  firstName={accountName.first}
                  lastName={accountName.last}
                  size={28}
                  className="bg-white/15 text-[11px] tracking-wide text-white ring-1 ring-white/40"
                />
              ) : (
                <UserRoundIcon className="size-4" />
              )}
            </DropdownMenuTrigger>
            {/* Explicit width: the default tracks the trigger's, which crushes
                the email onto a 128px menu. */}
            <DropdownMenuContent align="end" sideOffset={8} className="w-72 p-1.5">
              {principal && accountName && (
                <>
                  <DropdownMenuGroup>
                    <DropdownMenuLabel className="flex items-center gap-3 px-2 py-2">
                      <EmployeeAvatar
                        avatarUrl={principal.avatar_url}
                        firstName={accountName.first}
                        lastName={accountName.last}
                        size={40}
                        className="bg-brand-primary text-sm text-white"
                      />
                      <span className="flex min-w-0 flex-col gap-0.5">
                        <span className="truncate text-sm font-medium text-foreground" title={principal.email}>
                          {principal.email}
                        </span>
                        <span className="text-xs font-normal text-muted-foreground">
                          {principal.role === 'hr_admin' ? 'HR admin' : 'Viewer'}
                        </span>
                      </span>
                    </DropdownMenuLabel>
                  </DropdownMenuGroup>
                  <DropdownMenuSeparator className="my-1.5" />
                </>
              )}
              <DropdownMenuItem onClick={() => navigate('/profile')} className="gap-2 px-2 py-2">
                <UserRoundIcon /> Your profile
              </DropdownMenuItem>
              <DropdownMenuItem onClick={logout} className="gap-2 px-2 py-2">
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

      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  )
}
