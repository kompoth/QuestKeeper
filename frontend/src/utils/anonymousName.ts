import { adjectives, animals, uniqueNamesGenerator } from 'unique-names-generator'

/**
 * A friendly placeholder name (e.g. "Clever Otter") for a user whose real name isn't known yet.
 * Deterministic per seed, but not persisted - the same seed always yields the same name within a
 * session, matching Google Docs' anonymous-viewer naming.
 */
export function anonymousName (seed: string): string {
  return uniqueNamesGenerator({ dictionaries: [adjectives, animals], seed, separator: ' ', style: 'capital' })
}
