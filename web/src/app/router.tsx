import { createBrowserRouter, Navigate } from 'react-router'
import { AnalyticsPage } from '@/features/analytics/AnalyticsPage'
import { LoginPage } from '@/features/auth/LoginPage'
import { EmployeeDetailPage } from '@/features/employees/EmployeeDetailPage'
import { EmployeesListPage } from '@/features/employees/EmployeesListPage'
import { OrgChartPage } from '@/features/hierarchy/OrgChartPage'
import { ImportPage } from '@/features/import/ImportPage'
import { AppShell } from './AppShell'

// /login stands alone (no topbar/nav); everything else lives inside the
// app shell as a child route rendered through its <Outlet/>.
export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/chart" replace /> },
      { path: '/chart', element: <OrgChartPage /> },
      { path: '/employees', element: <EmployeesListPage /> },
      { path: '/employees/:id', element: <EmployeeDetailPage /> },
      { path: '/analytics', element: <AnalyticsPage /> },
      { path: '/import', element: <ImportPage /> },
      { path: '*', element: <Navigate to="/chart" replace /> },
    ],
  },
])
