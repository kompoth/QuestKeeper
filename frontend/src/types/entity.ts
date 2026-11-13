export interface EntityMarker {
  entityId: string
  x: number
  y: number
}

export interface EntityMapContent {
  image: string
  markers: EntityMarker[]
}

export interface EntityArticleContent {
  content: string
}

export interface Entity {
  id: string
  worldId: string
  parentId?: string
  title: string
  article?: EntityArticleContent
  map?: EntityMapContent
}

export interface EntitySummary {
  id: string
  worldId: string
  parentId?: string
  title: string
  hasMap: boolean
}
