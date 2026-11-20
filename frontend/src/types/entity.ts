export interface MapPin {
  entityId: string
  x: number
  y: number
}

export interface EntityMapContent {
  pic: string
  pins: MapPin[]
}

export interface EntityArticleContent {
  markdown: string
}

export interface EntityAccess {
  read: boolean
  write: boolean
  canDelete: boolean
}

export interface Entity {
  id: string
  worldId: string
  name: string
  parent: string | null
  children: string[]
  article: EntityArticleContent | null
  map: EntityMapContent | null
  createdAt: string | null
  updatedAt: string | null
  createdBy: string | null
  updatedBy: string | null
  deletedAt: string | null
  access: EntityAccess
}
