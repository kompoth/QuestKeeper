import type { Entity } from '@/types/entity'
import type { NavItem } from '@/types/nav-item'
import type { InjectionKey } from 'vue'

export interface NavItemHandlers {
  onRename: (entityId: string) => void
  onAddPage: (parentId: string) => void
  onDelete: (entityId: string) => void
}

export const refreshNavItemsKey: InjectionKey<() => Promise<void>> = Symbol('refreshNavItems')

export function toNavItem (
  worldId: string,
  entity: Entity,
  entitiesById: Map<string, Entity>,
  handlers: NavItemHandlers,
): NavItem {
  const children = entity.children
    .map(id => entitiesById.get(id))
    .filter((child): child is Entity => child !== undefined)

  return {
    id: entity.id,
    title: entity.name,
    to: `/w/${worldId}/e/${entity.id}`,
    icon: entity.map ? 'mdi-map' : 'mdi-file-document-outline',
    children: children.length > 0
      ? children.map(child => toNavItem(worldId, child, entitiesById, handlers))
      : undefined,
    // TODO: tailor which actions apply per entity (e.g. omit "Add page" once it already has one)
    actions: [
      { title: 'Rename', icon: 'mdi-form-textbox', onClick: () => handlers.onRename(entity.id) },
      { title: 'Add page', icon: 'mdi-file-plus', onClick: () => handlers.onAddPage(entity.id) },
      { title: 'Delete', icon: 'mdi-delete', onClick: () => handlers.onDelete(entity.id) },
    ],
  }
}
