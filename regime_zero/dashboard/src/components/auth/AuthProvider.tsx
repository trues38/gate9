"use client"

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { User, Session, AuthError } from '@supabase/supabase-js'

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  error: AuthError | null
  signInWithGoogle: () => Promise<void>
  signInWithEmail: (email: string, password: string) => Promise<{ error: AuthError | null }>
  signUp: (email: string, password: string, metadata?: { full_name?: string; phone?: string }) => Promise<{ error: AuthError | null }>
  signOut: () => Promise<void>
  resetPassword: (email: string) => Promise<{ error: AuthError | null }>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<AuthError | null>(null)

  const supabase = createClient()

  useEffect(() => {
    // Get initial session
    const initSession = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        if (error) throw error

        setSession(session)
        setUser(session?.user ?? null)
      } catch (err) {
        console.error('Error getting session:', err)
        setError(err as AuthError)
      } finally {
        setLoading(false)
      }
    }

    initSession()

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log('[Auth] Event:', event)
        setSession(session)
        setUser(session?.user ?? null)
        setError(null)

        // Handle specific events
        if (event === 'SIGNED_IN') {
          // Optionally sync user profile
        } else if (event === 'SIGNED_OUT') {
          // Clear any local state
        } else if (event === 'TOKEN_REFRESHED') {
          // Token was refreshed
        }
      }
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [supabase.auth])

  const signInWithGoogle = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/api/auth/callback`,
          queryParams: {
            access_type: 'offline',
            prompt: 'consent',
          }
        }
      })

      if (error) throw error
    } catch (err) {
      console.error('Google sign in error:', err)
      setError(err as AuthError)
    } finally {
      setLoading(false)
    }
  }, [supabase.auth])

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    setLoading(true)
    setError(null)

    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password
      })

      if (error) {
        setError(error)
        return { error }
      }

      return { error: null }
    } catch (err) {
      const error = err as AuthError
      setError(error)
      return { error }
    } finally {
      setLoading(false)
    }
  }, [supabase.auth])

  const signUp = useCallback(async (
    email: string,
    password: string,
    metadata?: { full_name?: string; phone?: string }
  ) => {
    setLoading(true)
    setError(null)

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: metadata,
          emailRedirectTo: `${window.location.origin}/api/auth/callback`
        }
      })

      if (error) {
        setError(error)
        return { error }
      }

      // Create profile if user created
      if (data.user) {
        await supabase.from('profiles').upsert({
          id: data.user.id,
          email,
          full_name: metadata?.full_name,
          phone: metadata?.phone,
          created_at: new Date().toISOString()
        })
      }

      return { error: null }
    } catch (err) {
      const error = err as AuthError
      setError(error)
      return { error }
    } finally {
      setLoading(false)
    }
  }, [supabase])

  const signOut = useCallback(async () => {
    setLoading(true)
    try {
      await supabase.auth.signOut()
    } catch (err) {
      console.error('Sign out error:', err)
      setError(err as AuthError)
    } finally {
      setLoading(false)
    }
  }, [supabase.auth])

  const resetPassword = useCallback(async (email: string) => {
    setLoading(true)
    setError(null)

    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`
      })

      if (error) {
        setError(error)
        return { error }
      }

      return { error: null }
    } catch (err) {
      const error = err as AuthError
      setError(error)
      return { error }
    } finally {
      setLoading(false)
    }
  }, [supabase.auth])

  const value = {
    user,
    session,
    loading,
    error,
    signInWithGoogle,
    signInWithEmail,
    signUp,
    signOut,
    resetPassword
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
