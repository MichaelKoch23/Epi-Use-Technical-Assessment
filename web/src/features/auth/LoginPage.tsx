import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff, LogIn } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupInput,
} from '@/components/ui/input-group'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import ehmLogo from '@/assets/ehm-logo.png'
import { apiClient } from '@/lib/apiClient'
import { getErrorMessage } from '@/lib/apiError'
import { setTokens } from '@/lib/auth'
import { meQueryKey } from './useAuth'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordVisible, setPasswordVisible] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const queryClient = useQueryClient()

  const loginMutation = useMutation({
    mutationFn: async () => {
      const { data, error: responseError } = await apiClient.POST('/api/v1/auth/login', {
        body: { email, password },
      })
      if (responseError) throw responseError
      return data
    },
    onSuccess: (data) => {
      setTokens(data.access_token, data.refresh_token)
      void queryClient.invalidateQueries({ queryKey: meQueryKey })
      const redirectTo = (location.state as { from?: string } | null)?.from ?? '/chart'
      navigate(redirectTo, { replace: true })
    },
    onError: (failure) => {
      setError(getErrorMessage(failure, 'Incorrect email or password'))
    },
  })

  const onSubmit = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    loginMutation.mutate()
  }

  const errorId = error ? 'login-error' : undefined

  return (
    <main className="flex min-h-svh items-center justify-center bg-surface-bg p-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <h1>
            <img src={ehmLogo} alt="EHM - Employee Hierarchy Management System" className="h-auto w-64" />
          </h1>
        </div>

        <div className="rounded-md border border-border bg-card p-6 shadow-sm">
          <h2 className="text-center font-display text-lg font-semibold text-foreground">Sign in</h2>

          <form onSubmit={onSubmit} className="mt-5 flex flex-col gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="email">Email address</Label>
              <Input
                id="email"
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(event) => {
                  setEmail(event.target.value)
                  setError(null)
                }}
                aria-invalid={Boolean(error)}
                aria-describedby={errorId}
                className="h-10"
              />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="password">Password</Label>
              <InputGroup className="h-10">
                <InputGroupInput
                  id="password"
                  type={passwordVisible ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(event) => {
                    setPassword(event.target.value)
                    setError(null)
                  }}
                  aria-invalid={Boolean(error)}
                  aria-describedby={errorId}
                  className="h-full"
                />
                <InputGroupAddon align="inline-end">
                  <InputGroupButton
                    size="icon-sm"
                    aria-label={passwordVisible ? 'Hide password' : 'Show password'}
                    aria-pressed={passwordVisible}
                    onClick={() => setPasswordVisible((visible) => !visible)}
                    className="relative text-muted-foreground after:absolute after:-inset-2 after:content-['']"
                  >
                    {passwordVisible ? <EyeOff /> : <Eye />}
                  </InputGroupButton>
                </InputGroupAddon>
              </InputGroup>
              {error && (
                <p id="login-error" role="alert" className="text-xs font-medium text-status-critical">
                  {error}
                </p>
              )}
            </div>
            <Button type="submit" disabled={loginMutation.isPending} className="mt-1 h-10">
              {loginMutation.isPending ? (
                <>
                  <Spinner /> Signing in...
                </>
              ) : (
                <>
                  <LogIn /> Sign in
                </>
              )}
            </Button>
          </form>
        </div>
      </div>
    </main>
  )
}
