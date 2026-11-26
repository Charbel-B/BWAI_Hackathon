import { createBrowserRouter } from 'react-router'

import { paths } from './paths'

import { AppShell } from '@/components/app-shell'
import { LoginPage } from '@/features/auth/login-page'
import { LandingPage } from '@/features/landing/landing-page'
import { RequireAuth } from '@/features/auth/require-auth'
import { AuditPage } from '@/features/audit/audit-page'
import { DashboardPage } from '@/features/invoices/dashboard-page'
import { InvoicePage } from '@/features/invoices/invoice-page'
import { ImportPage } from '@/features/import/import-page'
import { CollectionPage } from '@/features/collection/collection-page'
import { PrintPage } from '@/features/print/print-page'
import { SettingsPage } from '@/features/settings/settings-page'
import { VerificationPage } from '@/features/verification/verification-page'

export const router = createBrowserRouter([
  { path: paths.landing, element: <LandingPage /> },
  { path: paths.login, element: <LoginPage /> },
  { path: paths.verifyPattern, element: <VerificationPage /> },
  {
    element: <RequireAuth />,
    children: [
      { path: paths.invoicePrintPattern, element: <PrintPage /> },
      {
        element: <AppShell />,
        children: [
          { path: paths.dashboard, element: <DashboardPage /> },
          { path: paths.import, element: <ImportPage /> },
          { path: paths.invoicePattern, element: <InvoicePage /> },
          { path: paths.collection, element: <CollectionPage /> },
          { path: paths.audit, element: <AuditPage /> },
          { path: paths.settings, element: <SettingsPage /> },
        ],
      },
    ],
  },
])
