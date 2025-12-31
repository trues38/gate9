import neo4j, { Driver, Session, Record as Neo4jRecord } from 'neo4j-driver'

// Neo4j connection configurations
const NEO4J_CONFIG = {
  sports: {
    uri: process.env.NEO4J_SPORTS_URI || 'bolt://localhost:7687',
    user: process.env.NEO4J_USER || 'neo4j',
    password: process.env.NEO4J_PASSWORD || 'password123'
  },
  economy: {
    uri: process.env.NEO4J_ECONOMY_URI || 'bolt://localhost:7475',
    user: process.env.NEO4J_USER || 'neo4j',
    password: process.env.NEO4J_PASSWORD || 'password123'
  }
}

// Driver cache
const drivers: Record<string, Driver> = {}

export function getDriver(type: 'sports' | 'economy'): Driver {
  if (!drivers[type]) {
    const config = NEO4J_CONFIG[type]
    drivers[type] = neo4j.driver(
      config.uri,
      neo4j.auth.basic(config.user, config.password),
      {
        maxConnectionLifetime: 30 * 60 * 1000, // 30 minutes
        maxConnectionPoolSize: 50,
        connectionAcquisitionTimeout: 10000
      }
    )
  }
  return drivers[type]
}

export async function closeDrivers() {
  for (const driver of Object.values(drivers)) {
    await driver.close()
  }
}

// Graph node interface
export interface GraphNode {
  id: string
  label: string
  name: string
  cluster: 'sports' | 'economy'
  subCluster?: string
  color?: string
  size?: number
  [key: string]: unknown
}

// Graph link interface
export interface GraphLink {
  source: string
  target: string
  type: string
  weight?: number
}

// Graph data interface
export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

// Color palettes for clusters
const CLUSTER_COLORS = {
  sports: {
    NBA: '#ff6b6b',
    Soccer: '#4ecdc4',
    default: '#f39c12'
  },
  economy: {
    Macro: '#3498db',
    Regime: '#9b59b6',
    default: '#2ecc71'
  }
}

// Query sports graph data (NBA + Soccer)
export async function querySportsGraph(limit: number = 5000): Promise<GraphData> {
  const driver = getDriver('sports')
  const session = driver.session()

  try {
    // Query nodes
    const nodesResult = await session.run(`
      MATCH (n)
      WHERE n:Player OR n:Team OR n:Coach OR n:Match OR n:Manager
      RETURN
        toString(id(n)) as id,
        labels(n)[0] as label,
        COALESCE(n.name, n.abbr, n.abbreviation, 'Unknown') as name,
        properties(n) as props
      LIMIT $limit
    `, { limit: neo4j.int(limit) })

    // Query relationships
    const linksResult = await session.run(`
      MATCH (a)-[r]->(b)
      WHERE (a:Player OR a:Team OR a:Coach OR a:Match OR a:Manager)
        AND (b:Player OR b:Team OR b:Coach OR b:Match OR b:Manager)
      RETURN
        toString(id(a)) as source,
        toString(id(b)) as target,
        type(r) as type
      LIMIT $limit
    `, { limit: neo4j.int(limit * 2) })

    const nodes: GraphNode[] = nodesResult.records.map((record: Neo4jRecord) => {
      const label = record.get('label')
      const isNBA = ['Player', 'Coach', 'Team'].includes(label) && !record.get('props')?.league
      const isSoccer = record.get('props')?.league || ['Manager', 'Match'].includes(label)

      const subCluster = isNBA ? 'NBA' : isSoccer ? 'Soccer' : 'default'
      const colors = CLUSTER_COLORS.sports

      return {
        id: record.get('id'),
        label,
        name: record.get('name'),
        cluster: 'sports' as const,
        subCluster,
        color: colors[subCluster as keyof typeof colors] || colors.default,
        size: label === 'Team' ? 8 : label === 'Player' ? 4 : 6,
        ...record.get('props')
      }
    })

    const links: GraphLink[] = linksResult.records.map((record: Neo4jRecord) => ({
      source: record.get('source'),
      target: record.get('target'),
      type: record.get('type')
    }))

    return { nodes, links }
  } finally {
    await session.close()
  }
}

// Query economy graph data
export async function queryEconomyGraph(limit: number = 5000): Promise<GraphData> {
  const driver = getDriver('economy')
  const session = driver.session()

  try {
    // Query nodes
    const nodesResult = await session.run(`
      MATCH (n)
      RETURN
        toString(id(n)) as id,
        labels(n)[0] as label,
        COALESCE(n.name, n.title, n.id, 'Unknown') as name,
        properties(n) as props
      LIMIT $limit
    `, { limit: neo4j.int(limit) })

    // Query relationships
    const linksResult = await session.run(`
      MATCH (a)-[r]->(b)
      RETURN
        toString(id(a)) as source,
        toString(id(b)) as target,
        type(r) as type
      LIMIT $limit
    `, { limit: neo4j.int(limit * 2) })

    const nodes: GraphNode[] = nodesResult.records.map((record: Neo4jRecord) => {
      const label = record.get('label')
      const isMacro = ['Indicator', 'Country', 'Currency'].includes(label)
      const isRegime = ['Regime', 'Pattern', 'Event'].includes(label)

      const subCluster = isMacro ? 'Macro' : isRegime ? 'Regime' : 'default'
      const colors = CLUSTER_COLORS.economy

      return {
        id: record.get('id'),
        label,
        name: record.get('name'),
        cluster: 'economy' as const,
        subCluster,
        color: colors[subCluster as keyof typeof colors] || colors.default,
        size: label === 'Regime' ? 8 : 5,
        ...record.get('props')
      }
    })

    const links: GraphLink[] = linksResult.records.map((record: Neo4jRecord) => ({
      source: record.get('source'),
      target: record.get('target'),
      type: record.get('type')
    }))

    return { nodes, links }
  } finally {
    await session.close()
  }
}

// Combine sports and economy graphs with cluster offsets
export async function queryClusteredGraph(
  sportsLimit: number = 3000,
  economyLimit: number = 3000
): Promise<GraphData> {
  const [sportsData, economyData] = await Promise.all([
    querySportsGraph(sportsLimit).catch(() => ({ nodes: [], links: [] })),
    queryEconomyGraph(economyLimit).catch(() => ({ nodes: [], links: [] }))
  ])

  // Prefix IDs to avoid conflicts
  const sportsNodes = sportsData.nodes.map(n => ({
    ...n,
    id: `sports_${n.id}`
  }))

  const sportsLinks = sportsData.links.map(l => ({
    ...l,
    source: `sports_${l.source}`,
    target: `sports_${l.target}`
  }))

  const economyNodes = economyData.nodes.map(n => ({
    ...n,
    id: `economy_${n.id}`
  }))

  const economyLinks = economyData.links.map(l => ({
    ...l,
    source: `economy_${l.source}`,
    target: `economy_${l.target}`
  }))

  return {
    nodes: [...sportsNodes, ...economyNodes],
    links: [...sportsLinks, ...economyLinks]
  }
}
