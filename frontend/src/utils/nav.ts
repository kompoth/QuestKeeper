import type { EntitySummary } from '@/types/entity'
import type { NavItem } from '@/types/nav-item'
import type { InjectionKey } from 'vue'
import { listChildEntities } from '@/data/entities'

export interface NavItemHandlers {
  onRename: (entityId: string) => void
  onAddPage: (parentId: string) => void
  onDelete: (entityId: string) => void
}

export const refreshNavItemsKey: InjectionKey<() => Promise<void>> = Symbol('refreshNavItems')

export async function toNavItem (worldId: string, entity: EntitySummary, handlers: NavItemHandlers): Promise<NavItem> {
  const children = await listChildEntities(entity.id)

  return {
    id: entity.id,
    title: entity.title,
    to: `/w/${worldId}/e/${entity.id}`,
    icon: entity.hasMap ? 'mdi-map' : 'mdi-file-document-outline',
    children: children.length > 0
      ? await Promise.all(children.map(child => toNavItem(worldId, child, handlers)))
      : undefined,
    // TODO: tailor which actions apply per entity (e.g. omit "Add page" once it already has one)
    actions: [
      { title: 'Rename', icon: 'mdi-form-textbox', onClick: () => handlers.onRename(entity.id) },
      { title: 'Add page', icon: 'mdi-file-plus', onClick: () => handlers.onAddPage(entity.id) },
      { title: 'Delete', icon: 'mdi-delete', onClick: () => handlers.onDelete(entity.id) },
    ],
  }
}
