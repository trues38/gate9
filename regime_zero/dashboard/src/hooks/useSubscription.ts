"use client"

import { useState, useEffect, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import { useAuth } from '@/components/auth/AuthProvider'

export interface Subscription {
  id: string
  user_id: string
  plan: 'trial' | 'week' | 'month'
  status: 'active' | 'expired' | 'canceled'
  expires_at: string
  lemon_order_id: string | null
  created_at: string
}

interface UseSubscriptionReturn {
  subscription: Subscription | null
  isActive: boolean
  isLoading: boolean
  error: Error | null
  daysRemaining: number
  refresh: () => Promise<void>
}

export function useSubscription(): UseSubscriptionReturn {
  const { user } = useAuth()
  const [subscription, setSubscription] = useState<Subscription | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const supabase = createClient()

  const fetchSubscription = useCallback(async () => {
    if (!user) {
      setSubscription(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const { data, error: fetchError } = await supabase
        .from('subscriptions')
        .select('*')
        .eq('user_id', user.id)
        .eq('status', 'active')
        .gte('expires_at', new Date().toISOString())
        .order('expires_at', { ascending: false })
        .limit(1)
        .single()

      if (fetchError && fetchError.code !== 'PGRST116') {
        throw fetchError
      }

      setSubscription(data)
    } catch (err) {
      console.error('Error fetching subscription:', err)
      setError(err as Error)
      setSubscription(null)
    } finally {
      setIsLoading(false)
    }
  }, [user, supabase])

  useEffect(() => {
    fetchSubscription()
  }, [fetchSubscription])

  // Calculate days remaining
  const daysRemaining = subscription
    ? Math.max(0, Math.ceil(
        (new Date(subscription.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      ))
    : 0

  const isActive = !!subscription && subscription.status === 'active' && daysRemaining > 0

  return {
    subscription,
    isActive,
    isLoading,
    error,
    daysRemaining,
    refresh: fetchSubscription
  }
}

// Plan details helper
export const PLAN_DETAILS = {
  trial: {
    name: 'Trial Pass',
    duration: 3,
    price: 19,
    features: ['Basic match access', 'Standard reports']
  },
  week: {
    name: 'Week Pass',
    duration: 7,
    price: 29,
    features: ['Full match access', 'Detailed reports', 'Basic analytics']
  },
  month: {
    name: 'Month Pass',
    duration: 30,
    price: 99,
    features: ['All features', 'Push notifications', 'Priority support', 'API access']
  }
} as const
