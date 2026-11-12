import type { Entity, EntitySummary } from '@/types/entity'
import { listEntityTabs } from '@/types/entity'

const entities: Entity[] = [
  { id: '1', worldId: '1', title: 'Entity One', tabs: { Article: { kind: 'article', content: 'Placeholder entity' } } },
  { id: '2', worldId: '1', title: 'Entity Two', tabs: { Article: { kind: 'article', content: 'Placeholder entity' } } },
  {
    id: '4',
    worldId: '1',
    parentId: '2',
    title: 'Nested Entity',
    tabs: { Article: { kind: 'article', content: 'Placeholder nested entity' } },
  },
  {
    id: '5',
    worldId: '1',
    parentId: '4',
    title: 'Deeply Nested Entity',
    tabs: { Article: { kind: 'article', content: 'Placeholder deeply nested entity' } },
  },
  { id: '3', worldId: '2', title: 'Entity Three', tabs: { Article: { kind: 'article', content: 'Placeholder entity' } } },
  {
    id: '6',
    worldId: '1',
    title: 'World One Map',
    tabs: {
      Article: { kind: 'article', content: 'Placeholder description for the map.' },
      Map: {
        kind: 'map',
        map: {
          image: 'https://i.imgur.com/pCna5.jpeg',
          markers: [
            { entityId: '1', x: 30, y: 40 },
            { entityId: '2', x: 68, y: 60 },
          ],
        },
      },
    },
  },
]

function toSummary (entity: Entity): EntitySummary {
  return {
    id: entity.id,
    worldId: entity.worldId,
    parentId: entity.parentId,
    title: entity.title,
    tabKinds: listEntityTabs(entity),
  }
}

export async function listEntities (worldId: string): Promise<EntitySummary[]> {
  return entities.filter(entity => entity.worldId === worldId && !entity.parentId).map(entity => toSummary(entity))
}

export async function getEntity (id: string): Promise<Entity | undefined> {
  return entities.find(entity => entity.id === id)
}

export async function listChildEntities (parentId: string): Promise<EntitySummary[]> {
  return entities.filter(entity => entity.parentId === parentId).map(entity => toSummary(entity))
}
