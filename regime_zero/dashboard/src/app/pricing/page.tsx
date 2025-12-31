"use client"

import { useState, useEffect, Suspense } from 'react'
import Link from "next/link"
import { useRouter, useSearchParams } from 'next/navigation'
import { Check, ArrowLeft, Loader2, Zap, Crown, Rocket, AlertCircle, CheckCircle } from "lucide-react"
import { useAuth } from '@/components/auth/AuthProvider'
import { useSubscription, PLAN_DETAILS } from '@/hooks/useSubscription'

const PLANS = [
  {
    id: 'trial' as const,
    icon: Zap,
    popular: false,
    gradient: 'from-blue-500/20 to-purple-500/20'
  },
  {
    id: 'week' as const,
    icon: Crown,
    popular: true,
    gradient: 'from-emerald-500/20 to-cyan-500/20'
  },
  {
    id: 'month' as const,
    icon: Rocket,
    popular: false,
    gradient: 'from-orange-500/20 to-red-500/20'
  }
]

function PricingContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { user, loading: authLoading } = useAuth()
  const { subscription, isActive, daysRemaining } = useSubscription()

  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState('')

  const canceled = searchParams.get('canceled')
  const success = searchParams.get('success')

  useEffect(() => {
    if (canceled) {
      setError('Payment was canceled. Please try again.')
    }
  }, [canceled])

  const handlePurchase = async (planId: 'trial' | 'week' | 'month') => {
    if (!user) {
      router.push(`/login?redirect=/pricing`)
      return
    }

    setLoading(planId)
    setError('')

    try {
      const response = await fetch('/api/lemonsqueezy/create-checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: planId })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create checkout session')
      }

      // Redirect to Stripe Checkout
      window.location.href = data.url
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setLoading(null)
    }
  }

  // Show success message
  if (success) {
    return (
      <div className="min-h-screen bg-black text-white flex items-center justify-center p-4">
        <div className="text-center space-y-6 max-w-md">
          <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle className="w-10 h-10 text-emerald-500" />
          </div>
          <h1 className="text-3xl font-bold">Payment Successful!</h1>
          <p className="text-slate-400">
            Your subscription is now active. You have full access to all matches and reports.
          </p>
          <Link
            href="/matches"
            className="inline-block py-3 px-8 bg-emerald-600 hover:bg-emerald-500 rounded-lg font-bold transition-colors"
          >
            View Matches
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white p-6 md:p-8">
      <Link
        href="/"
        className="text-slate-500 hover:text-white transition-colors flex items-center gap-2 mb-8 md:mb-12"
      >
        <ArrowLeft size={20} /> Back to Home
      </Link>

      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12 md:mb-16">
          <h1 className="text-3xl md:text-4xl font-bold mb-4">Get Your Pass</h1>
          <p className="text-slate-400">Unlock premium match analysis and regime insights</p>

          {/* Active Subscription Badge */}
          {isActive && subscription && (
            <div className="mt-6 inline-flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/30 rounded-full">
              <CheckCircle className="w-4 h-4 text-emerald-500" />
              <span className="text-emerald-400 text-sm">
                Active: {PLAN_DETAILS[subscription.plan].name} - {daysRemaining} days remaining
              </span>
            </div>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="max-w-md mx-auto mb-8 flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400">
            <AlertCircle size={20} />
            <span className="text-sm">{error}</span>
          </div>
        )}

        {/* Pricing Cards */}
        <div className="grid md:grid-cols-3 gap-6 md:gap-8">
          {PLANS.map((planConfig) => {
            const plan = PLAN_DETAILS[planConfig.id]
            const Icon = planConfig.icon

            return (
              <div
                key={planConfig.id}
                className={`relative rounded-2xl p-6 md:p-8 flex flex-col transition-transform hover:scale-[1.02] ${
                  planConfig.popular
                    ? 'bg-gradient-to-br from-slate-900 to-slate-800 border-2 border-emerald-500/50'
                    : 'bg-slate-900/50 border border-slate-800'
                }`}
              >
                {/* Popular Badge */}
                {planConfig.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-black text-xs font-bold px-4 py-1 rounded-full">
                    BEST VALUE
                  </div>
                )}

                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${planConfig.gradient} flex items-center justify-center mb-4`}>
                  <Icon className={`w-6 h-6 ${planConfig.popular ? 'text-emerald-400' : 'text-slate-400'}`} />
                </div>

                {/* Name & Duration */}
                <h3 className={`text-xl font-bold ${planConfig.popular ? 'text-white' : 'text-slate-300'}`}>
                  {plan.name}
                </h3>
                <p className="text-slate-500 text-sm mt-1">{plan.duration} days access</p>

                {/* Price */}
                <div className="mt-4 mb-6">
                  <span className="text-4xl font-bold">${plan.price}</span>
                  <span className="text-slate-500 ml-2">one-time</span>
                </div>

                {/* Features */}
                <ul className="space-y-3 mb-8 flex-1">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-3 text-sm">
                      <Check
                        size={16}
                        className={`mt-0.5 flex-shrink-0 ${planConfig.popular ? 'text-emerald-500' : 'text-slate-500'}`}
                      />
                      <span className={planConfig.popular ? 'text-white' : 'text-slate-300'}>
                        {feature}
                      </span>
                    </li>
                  ))}
                </ul>

                {/* Button */}
                <button
                  onClick={() => handlePurchase(planConfig.id)}
                  disabled={loading === planConfig.id || authLoading}
                  className={`w-full py-3 rounded-lg font-bold transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                    planConfig.popular
                      ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                      : 'border border-slate-700 hover:bg-slate-800 text-white'
                  }`}
                >
                  {loading === planConfig.id ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      <span>Processing...</span>
                    </>
                  ) : (
                    'Get Pass'
                  )}
                </button>
              </div>
            )
          })}
        </div>

        {/* Trust Badges */}
        <div className="mt-12 text-center">
          <p className="text-slate-500 text-sm mb-4">Secure payment powered by Stripe</p>
          <div className="flex items-center justify-center gap-6 text-slate-600">
            <span className="flex items-center gap-2 text-xs">
              <Check size={14} className="text-emerald-500" /> Instant Access
            </span>
            <span className="flex items-center gap-2 text-xs">
              <Check size={14} className="text-emerald-500" /> No Subscription
            </span>
            <span className="flex items-center gap-2 text-xs">
              <Check size={14} className="text-emerald-500" /> Secure Checkout
            </span>
          </div>
        </div>

        {/* Not logged in notice */}
        {!user && !authLoading && (
          <div className="mt-8 text-center">
            <p className="text-slate-500 text-sm">
              <Link href="/login" className="text-emerald-500 hover:underline">Sign in</Link>
              {' '}or{' '}
              <Link href="/signup" className="text-emerald-500 hover:underline">create an account</Link>
              {' '}to purchase
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Pricing() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-black flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-emerald-500" />
      </div>
    }>
      <PricingContent />
    </Suspense>
  )
}
