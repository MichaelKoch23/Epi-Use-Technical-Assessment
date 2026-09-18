import { useEffect, useState, type ComponentType } from 'react'
import {
  ArrowRightIcon,
  BadgeCheckIcon,
  CheckIcon,
  ExternalLinkIcon,
  ImageIcon,
  LockIcon,
  UserRoundXIcon,
  UsersIcon,
} from 'lucide-react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { AvatarEditor } from '@/components/avatar-editor'
import { EmployeeAvatar } from '@/components/employee-avatar'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/features/analytics/components/EmptyState'
import { ErrorState } from '@/features/analytics/components/ErrorState'
import { formatDate } from '@/features/employees/format'
import { getErrorMessage } from '@/lib/apiError'
import { nameFromEmail } from '@/lib/emailName'
import { cn } from '@/lib/utils'
import { useProfile, useProfileAvatarMutation, type Profile, type ProfilePerson } from './api'

const ROLE_LABELS: Record<string, string> = {
  hr_admin: 'HR admin',
  viewer: 'Viewer',
}

type ImageStatus = 'loading' | 'found' | 'missing'

function useImageStatus(url: string): ImageStatus {
  const [result, setResult] = useState<{ url: string; status: ImageStatus }>({
    url,
    status: 'loading',
  })
  useEffect(() => {
    let cancelled = false
    const image = new Image()
    image.onload = () => !cancelled && setResult({ url, status: 'found' })
    image.onerror = () => !cancelled && setResult({ url, status: 'missing' })
    image.src = url
    return () => {
      cancelled = true
    }
  }, [url])
  return result.url === url ? result.status : 'loading'
}

function Card({
  title,
  icon: Icon,
  children,
  className,
}: {
  title: string
  icon: ComponentType<{ className?: string }>
  children: React.ReactNode
  className?: string
}) {
  return (
    <section className={cn('rounded-md border border-border bg-card px-5 py-4', className)}>
      <h2 className="font-display mb-4 flex items-center gap-2 text-sm font-bold text-brand-primary">
        <Icon className="size-4" />
        {title}
      </h2>
      {children}
    </section>
  )
}

function PersonLink({ person, caption }: { person: ProfilePerson; caption?: string }) {
  return (
    <Link
      to={`/employees/${person.id}`}
      className="group flex items-center gap-3 rounded-md p-2 no-underline hover:bg-muted"
    >
      <EmployeeAvatar
        avatarUrl={person.avatar_url}
        firstName={person.first_name}
        lastName={person.last_name}
        size={36}
      />
      <span className="flex min-w-0 flex-col">
        {caption && <span className="text-xs text-muted-foreground">{caption}</span>}
        <span className="truncate text-sm font-medium text-foreground">
          {person.first_name} {person.last_name}
        </span>
        <span className="truncate text-xs text-muted-foreground">{person.position}</span>
      </span>
      <ArrowRightIcon className="ml-auto size-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
    </Link>
  )
}

function SourceRow({
  label,
  detail,
  active,
  preview,
}: {
  label: string
  detail: React.ReactNode
  active: boolean
  preview: React.ReactNode
}) {
  return (
    <li
      className={cn(
        'flex items-center gap-3 rounded-md border p-3',
        active ? 'border-brand-steel bg-brand-steel/10' : 'border-border'
      )}
    >
      <span className="grid size-10 shrink-0 place-items-center overflow-hidden rounded-full bg-muted text-muted-foreground">
        {preview}
      </span>
      <span className="flex min-w-0 flex-col">
        <span className="text-sm font-medium text-foreground">{label}</span>
        <span className="text-xs text-muted-foreground">{detail}</span>
      </span>
      {active && (
        <Badge className="ml-auto shrink-0 bg-brand-primary text-white">In use</Badge>
      )}
    </li>
  )
}

function PictureCard({ profile, initials }: { profile: Profile; initials: string }) {
  const gravatar = useImageStatus(profile.gravatar_url)
  const gravatarActive = !profile.has_uploaded_avatar && gravatar === 'found'

  return (
    <Card title="Profile picture" icon={ImageIcon}>
      <p className="mb-3 text-sm text-muted-foreground">
        The first of these that exists is shown everywhere your account appears.
      </p>
      <ol className="flex flex-col gap-2">
        <SourceRow
          label="1. Uploaded photo"
          active={profile.has_uploaded_avatar}
          detail={profile.has_uploaded_avatar ? 'Stored with your account' : 'None uploaded yet'}
          preview={
            profile.has_uploaded_avatar ? (
              <img src={profile.avatar_url} alt="" className="size-full object-cover" />
            ) : (
              <ImageIcon className="size-4" />
            )
          }
        />
        <SourceRow
          label="2. Gravatar"
          active={gravatarActive}
          detail={
            gravatar === 'loading' ? (
              'Checking...'
            ) : gravatar === 'found' ? (
              <>Found for {profile.email}</>
            ) : (
              <>
                None for {profile.email} -{' '}
                <a
                  href="https://gravatar.com/"
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-0.5 font-medium text-brand-mid underline-offset-2 hover:underline"
                >
                  create one <ExternalLinkIcon className="size-3" />
                </a>
              </>
            )
          }
          preview={
            gravatar === 'found' ? (
              <img src={profile.gravatar_url} alt="" className="size-full object-cover" />
            ) : (
              <UserRoundXIcon className="size-4" />
            )
          }
        />
        <SourceRow
          label="3. Initials"
          active={!profile.has_uploaded_avatar && gravatar === 'missing'}
          detail="Used when there is no picture"
          preview={
            <span className="grid size-full place-items-center bg-brand-steel text-xs font-semibold text-brand-primary">
              {initials}
            </span>
          }
        />
      </ol>
    </Card>
  )
}

function AccessCard({ profile }: { profile: Profile }) {
  const permissions = [
    { label: 'Browse the org chart, employee list and analytics', allowed: true },
    { label: 'See salaries and payroll cost', allowed: profile.can_view_salary },
    { label: 'Create, edit, delete and import employees', allowed: profile.can_edit },
    { label: 'Change your own profile photo', allowed: true },
  ]
  return (
    <Card title="Access" icon={BadgeCheckIcon}>
      <p className="mb-3 text-sm text-muted-foreground">
        You're signed in as{' '}
        <span className="font-medium text-foreground">{ROLE_LABELS[profile.role] ?? profile.role}</span>.
      </p>
      <ul className="flex flex-col gap-2.5">
        {permissions.map(({ label, allowed }) => (
          <li key={label} className="flex items-start gap-2.5 text-sm">
            <span
              className={cn(
                'mt-px grid size-5 shrink-0 place-items-center rounded-full',
                allowed ? 'bg-status-safe/15 text-status-safe' : 'bg-muted text-muted-foreground'
              )}
            >
              {allowed ? <CheckIcon className="size-3" /> : <LockIcon className="size-3" />}
            </span>
            <span className={allowed ? 'text-foreground' : 'text-muted-foreground'}>{label}</span>
          </li>
        ))}
      </ul>
    </Card>
  )
}

function EmployeeRecordCard({ profile }: { profile: Profile }) {
  const employee = profile.employee
  if (!employee) {
    return (
      <EmptyState icon={UsersIcon} title="No linked employee record">
        Accounts are linked to the employee whose email matches. No current employee uses{' '}
        <span className="font-medium text-foreground">{profile.email}</span>
        {profile.can_edit ? ' - add one from the Employees page to link it.' : '.'}
      </EmptyState>
    )
  }

  return (
    <Card title="Your employee record" icon={UsersIcon}>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <PersonLink person={employee} />
          <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div>
              <dt className="text-muted-foreground">Employee number</dt>
              <dd className="font-medium text-foreground">{employee.employee_number}</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">On record since</dt>
              <dd className="font-medium text-foreground">{formatDate(employee.joined_at)}</dd>
            </div>
          </dl>
          {employee.manager ? (
            <div className="rounded-md border border-border">
              <PersonLink person={employee.manager} caption="Reports to" />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No manager - top of the organisation.</p>
          )}
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-foreground">
            Direct reports{' '}
            <span className="font-normal text-muted-foreground">({employee.direct_reports.length})</span>
          </p>
          {employee.direct_reports.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nobody reports to you directly.</p>
          ) : (
            <ul className="flex max-h-72 flex-col overflow-y-auto rounded-md border border-border p-1">
              {employee.direct_reports.map((person) => (
                <li key={person.id}>
                  <PersonLink person={person} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  )
}

function ProfileSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-52 w-full" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
      </div>
    </div>
  )
}

export function ProfilePage() {
  const query = useProfile()
  const avatarMutation = useProfileAvatarMutation()

  if (query.isPending) return <ProfileSkeleton />
  if (query.isError) {
    return (
      <ErrorState
        message={getErrorMessage(query.error, 'Failed to load your profile')}
        onRetry={() => query.refetch()}
      />
    )
  }

  const profile = query.data
  const name = profile.employee
    ? { first: profile.employee.first_name, last: profile.employee.last_name }
    : nameFromEmail(profile.email)
  const initials = `${name.first.charAt(0)}${name.last.charAt(0)}`.toUpperCase()

  function changePhoto(file: File | null) {
    avatarMutation.mutate(file, {
      onSuccess: () =>
        toast.success(file ? 'Profile photo updated' : 'Profile photo removed', {
          description: file
            ? 'It now appears everywhere your account is shown.'
            : 'Your Gravatar or initials will be shown instead.',
        }),
      onError: (error) =>
        toast.error('Could not update your photo', {
          description: getErrorMessage(error, 'Your current photo is unchanged. Try again in a moment.'),
        }),
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <section className="overflow-hidden rounded-md border border-border bg-card">
        <div className="h-24 bg-gradient-to-r from-surface-deep via-brand-primary to-brand-mid" />
        <div className="flex flex-col gap-4 px-5 pb-5 sm:flex-row sm:items-end">
          <AvatarEditor
            className="-mt-12"
            avatarUrl={profile.avatar_url}
            firstName={name.first}
            lastName={name.last}
            size={112}
            hasUpload={profile.has_uploaded_avatar}
            isBusy={avatarMutation.isPending}
            onUpload={changePhoto}
            onRemove={() => changePhoto(null)}
            layout="stack"
          />
          <div className="flex min-w-0 flex-1 flex-col gap-1 sm:pb-9">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="font-display text-2xl font-bold">
                {name.first} {name.last}
              </h1>
              <Badge variant="outline" className="border-brand-steel text-brand-mid">
                {ROLE_LABELS[profile.role] ?? profile.role}
              </Badge>
            </div>
            <p className="truncate text-muted-foreground">{profile.email}</p>
            {profile.employee && (
              <p className="text-sm text-foreground">{profile.employee.position}</p>
            )}
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <PictureCard profile={profile} initials={initials} />
        <AccessCard profile={profile} />
      </div>

      <EmployeeRecordCard profile={profile} />
    </div>
  )
}
