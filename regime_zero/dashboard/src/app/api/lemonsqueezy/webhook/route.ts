import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/server'
import {
  verifyWebhookSignature,
  parseWebhookEvent,
  getPlanFromVariantId,
  PASS_CONFIG
} from '@/lib/lemonsqueezy'

export async function POST(request: NextRequest) {
  try {
    const payload = await request.text()
    const signature = request.headers.get('x-signature') || ''

    // Verify webhook signature
    if (!verifyWebhookSignature(payload, signature)) {
      console.error('Invalid webhook signature')
      return NextResponse.json(
        { error: 'Invalid signature' },
        { status: 401 }
      )
    }

    const event = parseWebhookEvent(payload)
    const eventName = event.meta.event_name

    console.log('LemonSqueezy webhook:', eventName)

    // Handle order_created event (payment successful)
    if (eventName === 'order_created') {
      const { attributes } = event.data
      const customData = event.meta.custom_data

      const userId = customData?.user_id
      const planFromCustom = customData?.plan as keyof typeof PASS_CONFIG | undefined
      const variantId = attributes.variant_id

      // Get plan from custom data or variant ID
      const plan = planFromCustom || getPlanFromVariantId(variantId)

      if (!userId || !plan) {
        console.error('Missing user_id or plan in webhook data')
        return NextResponse.json(
          { error: 'Missing required data' },
          { status: 400 }
        )
      }

      const planConfig = PASS_CONFIG[plan]
      const expiresAt = new Date()
      expiresAt.setDate(expiresAt.getDate() + planConfig.duration)

      // Create subscription record
      const supabase = createAdminClient()

      // Check for existing active subscription
      const { data: existingSub } = await supabase
        .from('subscriptions')
        .select('*')
        .eq('user_id', userId)
        .eq('status', 'active')
        .single()

      if (existingSub) {
        // Extend existing subscription
        const currentExpiry = new Date(existingSub.expires_at)
        const newExpiry = currentExpiry > new Date()
          ? new Date(currentExpiry.getTime() + planConfig.duration * 24 * 60 * 60 * 1000)
          : expiresAt

        await supabase
          .from('subscriptions')
          .update({
            expires_at: newExpiry.toISOString(),
            plan: plan
          })
          .eq('id', existingSub.id)
      } else {
        // Create new subscription
        await supabase
          .from('subscriptions')
          .insert({
            user_id: userId,
            plan: plan,
            status: 'active',
            expires_at: expiresAt.toISOString(),
            lemon_order_id: String(attributes.order_id)
          })
      }

      console.log(`Subscription created/updated for user ${userId}, plan: ${plan}`)
    }

    // Handle subscription_expired event
    if (eventName === 'subscription_expired') {
      const customData = event.meta.custom_data
      const userId = customData?.user_id

      if (userId) {
        const supabase = createAdminClient()
        await supabase
          .from('subscriptions')
          .update({ status: 'expired' })
          .eq('user_id', userId)
          .eq('status', 'active')
      }
    }

    return NextResponse.json({ received: true })
  } catch (error) {
    console.error('Webhook error:', error)
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 500 }
    )
  }
}
