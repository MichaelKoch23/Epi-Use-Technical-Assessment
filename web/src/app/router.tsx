import { createBrowserRouter, Navigate } from 'react-router'
import { AppShell } from './AppShell'
import { RequireAuth } from './RequireAuth'

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: async () => ({ Component: (await import('@/features/auth/LoginPage')).LoginPage }),
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Navigate to="/chart" replace /> },
          {
            path: '/chart',
            lazy: async () => ({
              Component: (await import('@/features/hierarchy/OrgChartPage')).OrgChartPage,
            }),
          },
          {
            path: '/employees',
            lazy: async () => ({
              Component: (await import('@/features/employees/EmployeesListPage')).EmployeesListPage,
            }),
          },
          {
            path: '/employees/:id',
            lazy: async () => ({
              Component: (await import('@/features/employees/EmployeeDetailPage')).EmployeeDetailPage,
            }),
          },
          {
            path: '/analytics',
            lazy: async () => ({
              Component: (await import('@/features/analytics/AnalyticsPage')).AnalyticsPage,
            }),
          },
          {
            path: '/import',
            lazy: async () => ({ Component: (await import('@/features/import/ImportPage')).ImportPage }),
          },
          {
            path: '/history',
            lazy: async () => ({
              Component: (await import('@/features/audit/GlobalAuditPage')).GlobalAuditPage,
            }),
          },
          {
            path: '/profile',
            lazy: async () => ({ Component: (await import('@/features/profile/ProfilePage')).ProfilePage }),
          },
          { path: '*', element: <Navigate to="/chart" replace /> },
        ],
      },
    ],
  },
])
