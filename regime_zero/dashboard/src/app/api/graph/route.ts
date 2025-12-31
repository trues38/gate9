import { NextRequest, NextResponse } from 'next/server'
import {
  querySportsGraph,
  queryEconomyGraph,
  queryClusteredGraph,
  GraphData
} from '@/lib/neo4j'

export const dynamic = 'force-dynamic'
export const revalidate = 300 // Cache for 5 minutes

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const type = searchParams.get('type') || 'all'
  const limit = Math.min(
    parseInt(searchParams.get('limit') || '5000', 10),
    10000 // Max limit
  )

  try {
    let data: GraphData

    switch (type) {
      case 'sports':
        data = await querySportsGraph(limit)
        break

      case 'economy':
        data = await queryEconomyGraph(limit)
        break

      case 'all':
      default:
        data = await queryClusteredGraph(
          Math.floor(limit / 2),
          Math.floor(limit / 2)
        )
        break
    }

    return NextResponse.json(data, {
      headers: {
        'Cache-Control': 'public, s-maxage=300, stale-while-revalidate=600'
      }
    })
  } catch (error) {
    console.error('Graph query error:', error)

    // Return empty data with fallback to static files
    return NextResponse.json(
      {
        nodes: [],
        links: [],
        error: 'Failed to fetch graph data',
        fallback: true
      },
      { status: 500 }
    )
  }
}
