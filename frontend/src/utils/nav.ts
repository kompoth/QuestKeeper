import type { Entity } from '@/types/entity'
import type { NavAction, NavItem } from '@/types/nav-item'
import type { InjectionKey, Ref } from 'vue'

export interface NavItemHandlers {
  onRename: (entityId: string) => void
  onAddPage: (parentId: string) => void
  onDelete: (entityId: string) => void
  onPermissions: (entityId: string) => void
}

export interface TrashNavItemHandlers {
  onRestore: (entityId: string) => void
  onRestoreBranch: (entityId: string) => void
  onPurge: (entityId: string) => void
}

export const refreshNavItemsKey: InjectionKey<() => Promise<void>> = Symbol('refreshNavItems')
export const isWorldOwnerKey: InjectionKey<Ref<boolean>> = Symbol('isWorldOwner')

// Bumped by World.vue whenever a trash/restore/purge action completes anywhere in the sidebar, so a
// trashed entity's own open page (EntityView) knows to re-fetch itself - its route doesn't change when
// that happens, so nothing else would tell it its "In Trash" status just changed.
export const entityTrashVersionKey: InjectionKey<Ref<number>> = Symbol('entityTrashVersion')

export function isEntityOrDescendant (entitiesById: Map<string, Entity>, ancestorId: string, candidateId: string): boolean {
  let current: string | undefined = candidateId
  while (current !== undefined) {
    if (current === ancestorId) {
      return true
    }
    current = entitiesById.get(current)?.parent ?? undefined
  }
  return false
}

function childrenOf (entity: Entity, entitiesById: Map<string, Entity>): Entity[] {
  return entity.children
    .map(id => entitiesById.get(id))
    .filter((child): child is Entity => child !== undefined)
}

export function toNavItem (
  worldId: string,
  entity: Entity,
  entitiesById: Map<string, Entity>,
  handlers: NavItemHandlers,
  isWorldOwner: boolean,
): NavItem {
  const children = childrenOf(entity, entitiesById)

  return {
    id: entity.id,
    title: entity.name,
    to: `/w/${worldId}/e/${entity.id}`,
    icon: entity.map ? 'mdi-map' : 'mdi-note-outline',
    children: children.length > 0
      ? children.map(child => toNavItem(worldId, child, entitiesById, handlers, isWorldOwner))
      : undefined,
    // TODO: tailor which actions apply per entity (e.g. omit "Add page" once it already has one)
    actions: [
      entity.access.write && { title: 'Rename', icon: 'mdi-form-textbox', onClick: () => handlers.onRename(entity.id) },
      entity.access.write && { title: 'Add page', icon: 'mdi-note-plus-outline', onClick: () => handlers.onAddPage(entity.id) },
      isWorldOwner && {
        title: 'Permissions', icon: 'mdi-account-key-outline', onClick: () => handlers.onPermissions(entity.id),
      },
      entity.access.canDelete && {
        title: 'To trash', icon: 'mdi-trash-can-outline', onClick: () => handlers.onDelete(entity.id),
      },
    ].filter((action): action is NavAction => action !== false),
  }
}

export function toTrashNavItem (
  worldId: string,
  entity: Entity,
  entitiesById: Map<string, Entity>,
  handlers: TrashNavItemHandlers,
): NavItem {
  const children = childrenOf(entity, entitiesById)

  return {
    id: entity.id,
    title: entity.name,
    to: `/w/${worldId}/e/${entity.id}`,
    icon: entity.map ? 'mdi-map' : 'mdi-note-outline',
    children: children.length > 0
      ? children.map(child => toTrashNavItem(worldId, child, entitiesById, handlers))
      : undefined,
    actions: entity.access.canDelete
      ? [
          { title: 'Restore', icon: 'mdi-restore', onClick: () => handlers.onRestore(entity.id) },
          {
            title: 'Restore branch', icon: 'mdi-backup-restore', onClick: () => handlers.onRestoreBranch(entity.id),
          },
          {
            title: 'Delete forever', icon: 'mdi-delete-forever', color: 'red', onClick: () => handlers.onPurge(entity.id),
          },
        ]
      : undefined,
  }
}
