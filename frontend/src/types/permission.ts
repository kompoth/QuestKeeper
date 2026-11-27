export type PermissionLevel = 'read' | 'write'

export interface EntityGrant {
  userId: string
  email: string
  name: string | null
  level: PermissionLevel
}

export interface InheritedEntityGrant extends EntityGrant {
  fromEntityId: string
}

export interface EntityPermissions {
  direct: EntityGrant[]
  inherited: InheritedEntityGrant[]
}
