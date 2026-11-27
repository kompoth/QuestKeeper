import type { Entity } from '@/types/entity'
import { describe, expect, it } from 'vitest'
import { isEntityOrDescendant } from '../nav'

function makeEntity (id: string, parent: string | null): Entity {
  return {
    id,
    worldId: 'world-1',
    name: id,
    parent,
    children: [],
    article: null,
    map: null,
    createdAt: null,
    updatedAt: null,
    createdBy: null,
    updatedBy: null,
    deletedAt: null,
    access: { read: true, write: true, canDelete: true },
  }
}

describe('isEntityOrDescendant', () => {
  const entitiesById = new Map([
    ['root', makeEntity('root', null)],
    ['child', makeEntity('child', 'root')],
    ['grandchild', makeEntity('grandchild', 'child')],
    ['unrelated', makeEntity('unrelated', null)],
  ])

  it('returns true when the candidate is the ancestor itself', () => {
    expect(isEntityOrDescendant(entitiesById, 'root', 'root')).toBe(true)
  })

  it('returns true when the candidate is a descendant', () => {
    expect(isEntityOrDescendant(entitiesById, 'root', 'grandchild')).toBe(true)
  })

  it('returns false when the candidate is unrelated', () => {
    expect(isEntityOrDescendant(entitiesById, 'root', 'unrelated')).toBe(false)
  })
})
