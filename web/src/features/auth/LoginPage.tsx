import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useLocation, useNavigate } from 'react-router'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'
import { setTokens } from '@/lib/auth'
import { meQueryKey } from './useAuth'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()

  const loginMutation = useMutation({
    mutationFn: async () => {
      const { data, error } = await apiClient.POST('/api/v1/auth/login', {
        body: { email, password },
      })
      if (error) throw error
      return data
    },
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
      void queryClient.invalidateQueries({ queryKey: meQueryKey })
      const redirectTo = (location.state as { from?: string } | null)?.from ?? '/chart'
      navigate(redirectTo, { replace: true })
    },
    onError: (error) => {
      toast.error(getErrorMessage(error, 'Incorrect email or password'))
    },
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    loginMutation.mutate()
  }

  return (
    <div className="grid min-h-svh place-items-center bg-background p-4">
      <div className="w-full max-w-sm rounded-lg border border-border bg-card p-6">
        <h1 className="font-display text-xl font-bold">Sign in</h1>
        <p className="mt-1 text-sm text-muted-foreground">Employee Hierarchy Manager</p>

        <form onSubmit={onSubmit} className="mt-6 flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>
          <Button type="submit" disabled={loginMutation.isPending}>
            {loginMutation.isPending ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </div>
    </div>
  )
}
