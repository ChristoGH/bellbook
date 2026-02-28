import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { api } from '../../lib/api'
import { setTokens } from '../../lib/auth'
import { queryClient } from '../../lib/query-client'
import { Button } from '../../components/ui/Button'
import { Input } from '../../components/ui/Input'
import type { TokenResponse } from '../../types'

type Tab = 'phone' | 'email'
type PhoneStep = 'number' | 'otp'

export default function LoginPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('phone')

  // Phone + OTP state
  const [phone, setPhone] = useState('')
  const [otp, setOtp] = useState('')
  const [phoneStep, setPhoneStep] = useState<PhoneStep>('number')

  // Email + password state
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleOtpRequest() {
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/otp/request', { phone })
      setPhoneStep('otp')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not send OTP')
    } finally {
      setLoading(false)
    }
  }

  async function handleOtpVerify() {
    setError('')
    setLoading(true)
    try {
      const data = await api.post<TokenResponse>('/auth/otp/verify', { phone, otp })
      setTokens(data.access_token, data.refresh_token)
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate('/', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Incorrect OTP')
    } finally {
      setLoading(false)
    }
  }

  async function handleEmailLogin() {
    setError('')
    setLoading(true)
    try {
      const data = await api.post<TokenResponse>('/auth/login', { email, password })
      setTokens(data.access_token, data.refresh_token)
      await queryClient.invalidateQueries({ queryKey: ['me'] })
      navigate('/', { replace: true })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-white text-2xl font-bold shadow-lg">
            B
          </div>
          <h1 className="text-2xl font-bold text-gray-900">BellBook</h1>
          <p className="mt-1 text-sm text-gray-500">School communication</p>
        </div>

        {/* Tab toggle */}
        <div className="mb-6 flex rounded-xl bg-gray-100 p-1">
          {(['phone', 'email'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(''); setPhoneStep('number') }}
              className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all ${
                tab === t ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'
              }`}
            >
              {t === 'phone' ? 'Phone (OTP)' : 'Email'}
            </button>
          ))}
        </div>

        {/* Phone flow */}
        {tab === 'phone' && (
          <div className="flex flex-col gap-4">
            {phoneStep === 'number' ? (
              <>
                <Input
                  label="Mobile number"
                  type="tel"
                  placeholder="+27 82 123 4567"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  error={error}
                />
                <Button onClick={handleOtpRequest} loading={loading} className="w-full" size="lg">
                  Send OTP
                </Button>
              </>
            ) : (
              <>
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
                <Button onClick={handleOtpVerify} loading={loading} className="w-full" size="lg">
                  Verify &amp; Sign in
                </Button>
                <button
                  className="text-center text-sm text-indigo-600"
                  onClick={() => setPhoneStep('number')}
                >
                  Change number
                </button>
              </>
            )}
          </div>
        )}

        {/* Email flow */}
        {tab === 'email' && (
          <div className="flex flex-col gap-4">
            <Input
              label="Email address"
              type="email"
              placeholder="teacher@school.co.za"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              error={error}
            />
            <Button onClick={handleEmailLogin} loading={loading} className="w-full" size="lg">
              Sign in
            </Button>
          </div>
        )}

        <p className="mt-6 text-center text-sm text-gray-500">
          New parent?{' '}
          <Link to="/register" className="font-medium text-indigo-600">
            Register here
          </Link>
        </p>
      </div>
    </div>
  )
}
