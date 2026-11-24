import { QueryClientProvider } from '@tanstack/react-query'
import { createBrowserRouter, RouterProvider } from 'react-router'

import { HealthStatus } from '@/features/health/health-status'

import { queryClient } from './query-client'

const router = createBrowserRouter([{ path: '/', element: <HealthStatus /> }])

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}
