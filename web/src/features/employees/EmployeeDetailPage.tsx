import { useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router'
import { toast } from 'sonner'
import { AvatarEditor } from '@/components/avatar-editor'
import { Badge } from '@/components/ui/badge'
import { EmployeeAvatar } from '@/components/employee-avatar'
import { useAuth } from '@/features/auth/useAuth'
import { ReportingLineBreadcrumb } from '@/features/hierarchy/ReportingLineBreadcrumb'
import { getErrorMessage } from '@/lib/apiError'
import { employeeKeys } from '@/lib/queryKeys'
import { AuditTimeline } from './AuditTimeline'
import { formatCurrency, formatDate } from './format'
import { fetchEmployee, useEmployeeAvatarMutation } from './mutations'

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { canEdit } = useAuth()
  const avatarMutation = useEmployeeAvatarMutation()

  const query = useQuery({
    queryKey: employeeKeys.detail(id ?? ''),
    queryFn: () => fetchEmployee(id ?? ''),
    enabled: Boolean(id),
  })

  if (!id) return null

  if (query.isPending) {
    return <p className="text-muted-foreground">Loading…</p>
  }
  if (query.isError || !query.data) {
    return <p className="text-muted-foreground">Could not load this employee.</p>
  }

  const employee = query.data
  const fullName = `${employee.first_name} ${employee.last_name}`

  function changePhoto(file: File | null) {
    avatarMutation.mutate(
      { id: employee.id, version: employee.version, file },
      {
        onSuccess: () => toast.success(file ? 'Photo updated' : 'Photo removed'),
        onError: (error) => toast.error(getErrorMessage(error, error.message || 'Could not update the photo')),
      }
    )
  }

  return (
    <div className="flex flex-col gap-6">
      {employee.manager_id && (
        <ReportingLineBreadcrumb
          employeeId={id}
          employeeName={fullName}
          onSelect={(managerId) => navigate(`/employees/${managerId}`)}
        />
      )}

      <div className="flex flex-wrap items-center gap-4">
        {canEdit && !employee.deleted_at ? (
          <AvatarEditor
            avatarUrl={employee.avatar_url}
            firstName={employee.first_name}
            lastName={employee.last_name}
            size={80}
            // Only an uploaded photo can be removed here; an external URL
            // override is managed from the edit form.
            hasUpload={employee.avatar_override_url?.startsWith('/api/v1/avatars/') ?? false}
            isBusy={avatarMutation.isPending}
            onUpload={changePhoto}
            onRemove={() => changePhoto(null)}
            layout="stack"
          />
        ) : (
          <EmployeeAvatar
            avatarUrl={employee.avatar_url}
            firstName={employee.first_name}
            lastName={employee.last_name}
            size={80}
          />
        )}
        <div className="flex flex-col gap-1 self-start pt-4">
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl font-bold">{fullName}</h1>
            {employee.deleted_at && <Badge variant="destructive">Deleted</Badge>}
          </div>
          <p className="text-muted-foreground">{employee.position}</p>
        </div>
      </div>

      <dl className="grid grid-cols-1 gap-x-8 gap-y-3 rounded-md border border-border p-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-muted-foreground">Employee number</dt>
          <dd className="font-medium text-foreground">{employee.employee_number}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Email</dt>
          <dd className="font-medium text-foreground">{employee.email}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Date of birth</dt>
          <dd className="font-medium text-foreground">{formatDate(employee.birth_date)}</dd>
        </div>
        {'salary' in employee && (
          <div>
            <dt className="text-muted-foreground">Salary</dt>
            <dd className="font-medium text-foreground">
              {formatCurrency(employee.salary, employee.currency)}
            </dd>
          </div>
        )}
      </dl>

      <AuditTimeline employeeId={id} />
    </div>
  )
}
