// LemonSqueezy API Client

const LEMONSQUEEZY_API_URL = 'https://api.lemonsqueezy.com/v1'

export const PASS_CONFIG = {
  trial: {
    name: '3-Day Trial',
    price: 19,
    duration: 3,
    variantId: process.env.LEMONSQUEEZY_TRIAL_VARIANT_ID || '',
    features: [
      'Full access to all matches',
      'Real-time regime analysis',
      'Basic graph visualization'
    ]
  },
  week: {
    name: '7-Day Pass',
    price: 29,
    duration: 7,
    variantId: process.env.LEMONSQUEEZY_WEEK_VARIANT_ID || '',
    features: [
      'Everything in Trial',
      'Advanced graph clusters',
      'Push notifications',
      'Priority support'
    ]
  },
  month: {
    name: '30-Day Pass',
    price: 99,
    duration: 30,
    variantId: process.env.LEMONSQUEEZY_MONTH_VARIANT_ID || '',
    features: [
      'Everything in Week Pass',
      'Historical data access',
      'API access',
      'Custom alerts',
      'Exclusive insights'
    ]
  }
} as const

export type PlanType = keyof typeof PASS_CONFIG

interface LemonSqueezyCheckoutResponse {
  data: {
    id: string
    type: 'checkouts'
    attributes: {
      url: string
      expires_at: string
    }
  }
}

interface LemonSqueezyWebhookEvent {
  meta: {
    event_name: string
    custom_data?: {
      user_id?: string
      plan?: string
    }
  }
  data: {
    id: string
    type: string
    attributes: {
      status: string
      user_email: string
      user_name: string
      variant_id: number
      order_id: number
      customer_id: number
      created_at: string
    }
  }
}

async function lemonSqueezyFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const apiKey = process.env.LEMONSQUEEZY_API_KEY

  if (!apiKey) {
    throw new Error('LEMONSQUEEZY_API_KEY is not configured')
  }

  const response = await fetch(`${LEMONSQUEEZY_API_URL}${endpoint}`, {
    ...options,
    headers: {
      'Accept': 'application/vnd.api+json',
      'Content-Type': 'application/vnd.api+json',
      'Authorization': `Bearer ${apiKey}`,
      ...options.headers,
    },
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`LemonSqueezy API error: ${response.status} - ${error}`)
  }

  return response.json()
}

export async function createCheckout(
  plan: PlanType,
  userId: string,
  userEmail: string,
  successUrl: string,
  cancelUrl: string
): Promise<string> {
  const storeId = process.env.LEMONSQUEEZY_STORE_ID
  const variantId = PASS_CONFIG[plan].variantId

  if (!storeId) {
    throw new Error('LEMONSQUEEZY_STORE_ID is not configured')
  }

  if (!variantId) {
    throw new Error(`Variant ID for plan "${plan}" is not configured`)
  }

  const response = await lemonSqueezyFetch<LemonSqueezyCheckoutResponse>('/checkouts', {
    method: 'POST',
    body: JSON.stringify({
      data: {
        type: 'checkouts',
        attributes: {
          checkout_data: {
            email: userEmail,
            custom: {
              user_id: userId,
              plan: plan
            }
          },
          checkout_options: {
            embed: false,
            media: false,
            button_color: '#10b981' // emerald-500
          },
          product_options: {
            enabled_variants: [parseInt(variantId)],
            redirect_url: successUrl,
          },
          expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString() // 1 hour
        },
        relationships: {
          store: {
            data: {
              type: 'stores',
              id: storeId
            }
          },
          variant: {
            data: {
              type: 'variants',
              id: variantId
            }
          }
        }
      }
    })
  })

  return response.data.attributes.url
}

export function verifyWebhookSignature(
  payload: string,
  signature: string
): boolean {
  const secret = process.env.LEMONSQUEEZY_WEBHOOK_SECRET

  if (!secret) {
    console.warn('LEMONSQUEEZY_WEBHOOK_SECRET not configured, skipping verification')
    return true
  }

  // LemonSqueezy uses HMAC SHA256
  const crypto = require('crypto')
  const hmac = crypto.createHmac('sha256', secret)
  const digest = hmac.update(payload).digest('hex')

  return crypto.timingSafeEqual(
    Buffer.from(signature),
    Buffer.from(digest)
  )
}

export function parseWebhookEvent(payload: string): LemonSqueezyWebhookEvent {
  return JSON.parse(payload)
}

export function getPlanFromVariantId(variantId: number): PlanType | null {
  for (const [plan, config] of Object.entries(PASS_CONFIG)) {
    if (config.variantId === String(variantId)) {
      return plan as PlanType
    }
  }
  return null
}
