export interface EntityMarker {
  entityId: string
  x: number
  y: number
}

export interface EntityMapContent {
  image: string
  markers: EntityMarker[]
}

export type EntityTab
  = | { kind: 'article', content: string }
    | { kind: 'map', map: EntityMapContent }

export interface Entity {
  id: string
  worldId: string
  parentId?: string
  title: string
  tabs: Record<string, EntityTab>
}

export function listEntityTabs (entity: Entity): Record<string, EntityTab['kind']> {
  return Object.fromEntries(
    Object.entries(entity.tabs).map(([name, tab]) => [name, tab.kind]),
  )
}

export interface EntitySummary {
  id: string
  worldId: string
  parentId?: string
  title: string
  tabKinds: Record<string, EntityTab['kind']>
}
