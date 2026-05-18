/* useFilters Tests */
import { describe, it, expect, vi, beforeEach } from 'vitest'

/* Mock the api module before importing useFilters */
const mockApiFetch = vi.hoisted(() => vi.fn())
let useSourceFilters
let useSecurityFilters

vi.mock('@/utils/api', () => ({
  apiFetch: mockApiFetch,
  API_PATHS: {
    connectedSourceSystems: '/api/connector/connected_source_systems',
    classifications: '/api/stochastic-analyzer/classifications'
  }
}))

async function reloadUseFilters() {
  vi.resetModules()
  const module = await import('../useFilters')
  useSourceFilters = module.useSourceFilters
  useSecurityFilters = module.useSecurityFilters
}

/* Helper: create a fake successful Response */
function fakeResponse(data, ok = true) {
  return {
    ok,
    statusText: ok ? 'OK' : 'Internal Server Error',
    json: () => Promise.resolve(data)
  }
}

describe('useSourceFilters', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await reloadUseFilters()
  })

  it('returns a ref that starts as an empty array', () => {
    mockApiFetch.mockReturnValue(new Promise(() => {})) // never resolves
    const result = useSourceFilters()
    expect(result.value).toEqual([])
  })

  it('fetches from the connectedSourceSystems endpoint', () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}))
    useSourceFilters()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/connector/connected_source_systems')
  })

  it('populates the ref with fetched source systems', async () => {
    const sources = ['GitLab', 'GitHub', 'Network File System']
    mockApiFetch.mockResolvedValue(fakeResponse(sources))

    const result = useSourceFilters()

    // Wait for the promise chain to resolve
    await vi.waitFor(() => {
      expect(result.value).toEqual(sources)
    })
  })

  it('keeps empty array when response is not ok', async () => {
    mockApiFetch.mockResolvedValue(fakeResponse(null, false))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSourceFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('keeps empty array when fetch throws a network error', async () => {
    mockApiFetch.mockRejectedValue(new Error('Network error'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSourceFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('creates a new ref on each call (not shared)', () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}))
    const a = useSourceFilters()
    const b = useSourceFilters()
    expect(a).not.toBe(b)
  })
})

describe('useSecurityFilters', () => {
  beforeEach(async () => {
    vi.clearAllMocks()
    await reloadUseFilters()
  })

  it('returns a ref that starts as an empty array', () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}))
    const result = useSecurityFilters()
    expect(result.value).toEqual([])
  })

  it('fetches from the classifications endpoint', () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}))
    useSecurityFilters()
    expect(mockApiFetch).toHaveBeenCalledWith('/api/stochastic-analyzer/classifications')
  })

  it('populates the ref with fetched classifications', async () => {
    const levels = ['Public', 'Internal', 'Sensitive', 'Confidential']
    mockApiFetch.mockResolvedValue(fakeResponse(levels))

    const result = useSecurityFilters()

    await vi.waitFor(() => {
      expect(result.value).toEqual(levels)
    })
  })

  it('keeps empty array when response is not ok', async () => {
    mockApiFetch.mockResolvedValue(fakeResponse(null, false))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('keeps empty array when fetch throws a network error', async () => {
    mockApiFetch.mockRejectedValue(new Error('Network error'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const result = useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })
    expect(result.value).toEqual([])
    consoleSpy.mockRestore()
  })

  it('logs error message when response is not ok', async () => {
    mockApiFetch.mockResolvedValue(fakeResponse(null, false))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Failed to fetch security classifications'))
    })
    consoleSpy.mockRestore()
  })

  it('logs error message when fetch throws', async () => {
    mockApiFetch.mockRejectedValue(new Error('Connection refused'))
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    useSecurityFilters()

    await vi.waitFor(() => {
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('Error fetching security classifications'))
    })
    consoleSpy.mockRestore()
  })

  it('returns the same ref on each call (shared cache)', () => {
    mockApiFetch.mockReturnValue(new Promise(() => {}))
    const a = useSecurityFilters()
    const b = useSecurityFilters()
    expect(a).toBe(b)
  })
})
