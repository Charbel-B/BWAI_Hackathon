import { createBrowserRouter } from 'react-router'

import { AppShell } from '@/components/app-shell'
import { LoginPage } from '@/features/auth/login-page'
import { RequireAuth } from '@/features/auth/require-auth'
import { AuditPage } from '@/features/audit/audit-page'
import { DashboardPage } from '@/features/invoices/dashboard-page'
import { InvoicePage } from '@/features/invoices/invoice-page'
import { ImportPage } from '@/features/import/import-page'

export const router = createBrowserRouter([
  { path: '/connexion', element: <LoginPage /> },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/', element: <DashboardPage /> },
          { path: '/importer', element: <ImportPage /> },
          { path: '/factures/:invoiceId', element: <InvoicePage /> },
          { path: '/journal', element: <AuditPage /> },
        ],
      },
    ],
  },
])
