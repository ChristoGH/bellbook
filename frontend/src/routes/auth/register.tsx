import { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { api } from '../../lib/api'
import { setTokens } from '../../lib/auth'
import { queryClient } from '../../lib/query-client'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import type { TokenResponse } from '../../types'

type Step = 'otp-request' | 'otp-verify'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const schoolId = params.get('school_id') ?? ''

  const [step, setStep] = useState<Step>('otp-request')
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function requestOtp() {
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/otp/request', { phone })
      setStep('otp-verify')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send OTP')
    } finally {
      setLoading(false)
    }
  }

  async function register() {
    setError('')
    if (!schoolId) {
      setError('Invalid invite link — school ID is missing.')
      return
    }
    setLoading(true)
    try {
      const data = await api.post<TokenResponse>('/auth/register', {
        phone,
        otp,
        first_name: firstName,
        last_name: lastName,
        school_id: schoolId,
      })
      setTokens(data.access_token, data.refresh_token)
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate('/', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-white text-2xl font-bold shadow-lg">
            B
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Create account</h1>
          <p className="mt-1 text-sm text-gray-500">Join your school on BellBook</p>
        </div>

        {step === 'otp-request' ? (
          <div className="flex flex-col gap-4">
            <Input
              label="First name"
              placeholder="Sipho"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
            <Input
              label="Last name"
              placeholder="Mokoena"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
            <Input
              label="Mobile number"
              type="tel"
              placeholder="+27 82 123 4567"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              error={error}
              hint="We'll send a one-time PIN to verify your number"
            />
            <Button onClick={requestOtp} loading={loading} className="w-full" size="lg">
              Send verification code
            </Button>
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            <p className="text-sm text-gray-600">
              Enter the 6-digit code sent to <strong>{phone}</strong>
            </p>
            <Input
              label="One-time PIN"
              type="number"
              inputMode="numeric"
              placeholder="123456"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              error={error}
            />
            <Button onClick={register} loading={loading} className="w-full" size="lg">
              Create account
            </Button>
            <button
              className="text-center text-sm text-indigo-600"
              onClick={() => setStep('otp-request')}
            >
              Change number
            </button>
          </div>
        )}

        <p className="mt-6 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-indigo-600">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
