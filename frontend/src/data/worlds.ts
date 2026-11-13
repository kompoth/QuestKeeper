import type { World } from '@/types/world'

const worlds: World[] = [
  { id: '1', name: 'World One', description: 'Placeholder world' },
  { id: '2', name: 'World Two', description: 'Placeholder world' },
  { id: '3', name: 'World Three', description: 'Placeholder world' },
]

export function listWorlds (): World[] {
  return [...worlds]
}

export function getWorld (id: string): World | undefined {
  return worlds.find(world => world.id === id)
}

export function createWorld (name: string, description: string): World {
  const world: World = { id: crypto.randomUUID(), name, description }
  worlds.push(world)
  return world
}

export function updateWorld (id: string, name: string, description: string): World | undefined {
  const world = getWorld(id)
  if (!world) {
    return undefined
  }
  world.name = name
  world.description = description
  return world
}
