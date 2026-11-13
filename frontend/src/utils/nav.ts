import type { EntitySummary } from '@/types/entity'
import type { NavItem } from '@/types/nav-item'
import { listChildEntities } from '@/data/entities'

export async function toNavItem (worldId: string, entity: EntitySummary): Promise<NavItem> {
  const children = await listChildEntities(entity.id)

  return {
    id: entity.id,
    title: entity.title,
    to: `/w/${worldId}/e/${entity.id}`,
    icon: entity.hasMap ? 'mdi-map' : 'mdi-file-document-outline',
    children: await Promise.all(children.map(child => toNavItem(worldId, child))),
  }
}
