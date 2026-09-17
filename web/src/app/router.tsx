import { createBrowserRouter, Navigate } from 'react-router'
import { AnalyticsPage } from '@/features/analytics/AnalyticsPage'
import { GlobalAuditPage } from '@/features/audit/GlobalAuditPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { EmployeeDetailPage } from '@/features/employees/EmployeeDetailPage'
import { EmployeesListPage } from '@/features/employees/EmployeesListPage'
import { OrgChartPage } from '@/features/hierarchy/OrgChartPage'
import { ImportPage } from '@/features/import/ImportPage'
import { ProfilePage } from '@/features/profile/ProfilePage'
import { AppShell } from './AppShell'
import { RequireAuth } from './RequireAuth'

// /login stands alone (no topbar/nav); everything else lives inside the
// app shell as a child route rendered through its <Outlet/>, gated by
// RequireAuth so a missing access token bounces to /login first.
export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="/chart" replace /> },
          { path: '/chart', element: <OrgChartPage /> },
          { path: '/employees', element: <EmployeesListPage /> },
          { path: '/employees/:id', element: <EmployeeDetailPage /> },
          { path: '/analytics', element: <AnalyticsPage /> },
          { path: '/import', element: <ImportPage /> },
          { path: '/history', element: <GlobalAuditPage /> },
          { path: '/profile', element: <ProfilePage /> },
          { path: '*', element: <Navigate to="/chart" replace /> },
        ],
      },
    ],
  },
])
