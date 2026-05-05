/* pkce module tests */
import { describe, it, expect } from 'vitest'
import { createPkcePair, generateState } from '@/utils/pkce'

describe('pkce', () => {
  describe('createPkcePair', () => {
    it('returns an object with verifier and challenge', async () => {
      const pair = await createPkcePair()
      expect(pair).toHaveProperty('verifier')
      expect(pair).toHaveProperty('challenge')
    })

    it('verifier is a non-empty string', async () => {
      const { verifier } = await createPkcePair()
      expect(typeof verifier).toBe('string')
      expect(verifier.length).toBeGreaterThan(0)
    })

    it('challenge is a non-empty string', async () => {
      const { challenge } = await createPkcePair()
      expect(typeof challenge).toBe('string')
      expect(challenge.length).toBeGreaterThan(0)
    })

    it('verifier and challenge are different', async () => {
      const { verifier, challenge } = await createPkcePair()
      expect(verifier).not.toBe(challenge)
    })

    it('generates unique pairs on each call', async () => {
      const pair1 = await createPkcePair()
      const pair2 = await createPkcePair()
      expect(pair1.verifier).not.toBe(pair2.verifier)
      expect(pair1.challenge).not.toBe(pair2.challenge)
    })

    it('uses only URL-safe base64 characters', async () => {
      const { verifier, challenge } = await createPkcePair()
      const urlSafe = /^[A-Za-z0-9_-]+$/
      expect(verifier).toMatch(urlSafe)
      expect(challenge).toMatch(urlSafe)
    })

    it('does not contain padding characters', async () => {
      const { verifier, challenge } = await createPkcePair()
      expect(verifier).not.toContain('=')
      expect(challenge).not.toContain('=')
    })
  })

  describe('generateState', () => {
    it('returns a non-empty string', () => {
      const state = generateState()
      expect(typeof state).toBe('string')
      expect(state.length).toBeGreaterThan(0)
    })

    it('generates unique values on each call', () => {
      const state1 = generateState()
      const state2 = generateState()
      expect(state1).not.toBe(state2)
    })

    it('uses only URL-safe base64 characters', () => {
      const state = generateState()
      const urlSafe = /^[A-Za-z0-9_-]+$/
      expect(state).toMatch(urlSafe)
    })

    it('does not contain padding characters', () => {
      const state = generateState()
      expect(state).not.toContain('=')
    })
  })
})
