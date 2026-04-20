import { describe, it, expect, vi, beforeEach } from 'vitest'

/* Mock the api module before importing useFilters */
const mockAuthFetch = vi.hoisted(() => vi.fn())

vi.mock('@/utils/api', () => ({
  authFetch: mockAuthFetch,
  API_PATHS: {
    connectedSourceSystems: '/api/connector/connected_source_systems',
    classifications: '/api/stochastic-analyzer/classifications'
  }
}))

import { useSourceFilters, useSecurityFilters } from '../useFilters'

/* Helper: create a fake successful Response */
function fakeResponse(data, ok = true) {
  return {
    ok,
    statusText: ok ? 'OK' : 'Internal Server Error',
    json: () => Promise.resolve(data)
  }
}

describe('useSourceFilters', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns a ref that starts as an empty array', () => {
    mockAuthFetch.mockReturnValue(new Promise(() => {})) // never resolves
    const result = useSourceFilters()
    expect(result.value).toEqual([])
  })

  it('fetches from the connectedSourceSystems endpoint', () => {
    mockAuthFetch.mockReturnValue(new Promise(() => {}))
    useSourceFilters()
    expect(mockAuthFetch).toHaveBeenCalledWith('/api/connector/connected_source_systems')
  })

  it('populates the ref with fetched source systems', async () => {
    const sources = ['GitLab', 'GitHub', 'Network File System']
    mockAuthFetch.mockResolvedValue(fakeResponse(sources))

    const result = useSourceFilters()

    // Wait for the promise chain to resolve
    await vi.waitFor(() => {
      expect(result.value).toEqual(sources)
    })
  })

  it('keeps empty array when response is not ok', async () => {
    mockAuthFetch.mockResolvedValue(fakeResponse(null, false))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSourceFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('keeps empty array when fetch throws a network error', async () => {
    mockAuthFetch.mockRejectedValue(new Error('Network error'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSourceFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('creates a new ref on each call (not shared)', () => {
    mockAuthFetch.mockReturnValue(new Promise(() => {}))
    const a = useSourceFilters()
    const b = useSourceFilters()
    expect(a).not.toBe(b)
  })
})

describe('useSecurityFilters', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns a ref that starts as an empty array', () => {
    mockAuthFetch.mockReturnValue(new Promise(() => {}))
    const result = useSecurityFilters()
    expect(result.value).toEqual([])
  })

  it('fetches from the classifications endpoint', () => {
    mockAuthFetch.mockReturnValue(new Promise(() => {}))
    useSecurityFilters()
    expect(mockAuthFetch).toHaveBeenCalledWith('/api/stochastic-analyzer/classifications')
  })

  it('populates the ref with fetched classifications', async () => {
    const levels = ['Public', 'Internal', 'Sensitive', 'Confidential']
    mockAuthFetch.mockResolvedValue(fakeResponse(levels))

    const result = useSecurityFilters()

    await vi.waitFor(() => {
      expect(result.value).toEqual(levels)
    })
  })

  it('keeps empty array when response is not ok', async () => {
    mockAuthFetch.mockResolvedValue(fakeResponse(null, false))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('keeps empty array when fetch throws a network error', async () => {
    mockAuthFetch.mockRejectedValue(new Error('Network error'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('logs error message when response is not ok', async () => {
    mockAuthFetch.mockResolvedValue(fakeResponse(null, false))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Failed to fetch security classifications')
      )
    })
    consoleSpy.mockRestore()
  })

  it('logs error message when fetch throws', async () => {
    mockAuthFetch.mockRejectedValue(new Error('Connection refused'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Error fetching security classifications')
      )
    })
    consoleSpy.mockRestore()
  })

  it('creates a new ref on each call (not shared)', () => {
    mockAuthFetch.mockReturnValue(new Promise(() => {}))
    const a = useSecurityFilters()
    const b = useSecurityFilters()
    expect(a).not.toBe(b)
  })
})