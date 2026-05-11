import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import SearchPreviewDrawer from '@/components/SearchPreviewDrawer.vue'

/* ── Mocks ── */

const mockMetadata = {
  previewTitle: ref('report.pdf'),
  previewFileDescription: ref('PDF Document'),
  sourceSystem: ref('SharePoint'),
  previewCreatedAt: ref('2025-03-12'),
  previewSize: ref(204800),
  previewLink: ref('https://example.com/report.pdf'),
  previewSecurityClass: ref('Internal'),
  uniquePointer: ref('ptr-abc-123')
}

vi.mock('@/composables/useSearchMetadata', () => ({
  useSearchMetadata: () => mockMetadata
}))

// the following two mocks are needed to prevent errors from the AI Summary and Rerank features,
// but the tests in this file don't interact with those features at all,
// so when I couldn´t fix it in other way I disableing eslint rules.

vi.mock('@/composables/aiSummary', () => {
  // eslint-disable-next-line no-undef
  const { ref } = require('vue')
  return {
    useAISummary: () => ({
      aiSummaryHtml: ref(''),
      summaryError: ref(''),
      isGeneratingSummary: ref(false),
      generateAISummary: vi.fn()
    })
  }
})

vi.mock('@/composables/aiRerank', () => {
  // eslint-disable-next-line no-undef
  const { ref } = require('vue')
  return {
    useAIRerank: () => ({
      aiRerankResultsComputed: ref([]),
      isReranking: ref(false),
      rerankError: ref(''),
      generateAIRerank: vi.fn()
    })
  }
})

const mockHasRole = vi.fn(() => false)
vi.mock('@/utils/auth', () => ({
  hasRole: (...args) => mockHasRole(...args)
}))

/* Component uses authFetch + API_PATHS, not saveClassification */
const mockAuthFetch = vi.fn()
vi.mock('@/utils/api', () => ({
  authFetch: (...args) => mockAuthFetch(...args),
  API_PATHS: {
    classification: '/api/stochastic-analyzer/classification'
  }
}))

/* ── Helpers ── */

const defaultProps = {
  open: true,
  selectedFile: 'report.pdf',
  selectedMatch: {
    name: 'report.pdf',
    unique_pointer: 'ptr-abc-123',
    security_class: 'Internal'
  },
  matches: []
}

const mountDrawer = (props = {}) =>
  mount(SearchPreviewDrawer, {
    props: { ...defaultProps, ...props },
    global: {
      stubs: {
        X: true,
        StarsIcon: true,
        CalendarDays: true,
        HardDrive: true,
        FileType2: true,
        ExternalLink: true,
        Pencil: true,
        CheckCircle: true,
        AlertCircle: true,
        Copy: true,
        /* Stub respects :visible so v-if toggling actually works */
        ClassificationEditor: {
          template: `
            <div v-if="visible" class="mock-editor">
              <button class="save-btn" @click="$emit('save', 'Confidential')">Save</button>
              <button class="cancel-btn" @click="$emit('cancel')">Cancel</button>
            </div>
          `,
          props: ['visible', 'currentLevel'],
          emits: ['save', 'cancel'],
          methods: { resetSaving: vi.fn() }
        },
        Transition: false
      },
      mocks: { $router: { push: vi.fn() } }
    }
  })

/* ═════════════════════════════════════════════ */

describe('SearchPreviewDrawer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockHasRole.mockReturnValue(false)

    /* Reset metadata to defaults between tests */
    mockMetadata.previewTitle.value = 'report.pdf'
    mockMetadata.previewFileDescription.value = 'PDF Document'
    mockMetadata.sourceSystem.value = 'SharePoint'
    mockMetadata.previewCreatedAt.value = '2025-03-12'
    mockMetadata.previewSize.value = 204800
    mockMetadata.previewLink.value = 'https://example.com/report.pdf'
    mockMetadata.previewSecurityClass.value = 'Internal'
    mockMetadata.uniquePointer.value = 'ptr-abc-123'
  })

  /* ─── Open / Close ─── */

  it('has "open" class when open prop is true', () => {
    const wrapper = mountDrawer()
    expect(wrapper.find('.preview-drawer').classes()).toContain('open')
  })

  it('lacks "open" class when closed', () => {
    const wrapper = mountDrawer({ open: false })
    expect(wrapper.find('.preview-drawer').classes()).not.toContain('open')
  })

  it('renders backdrop only when open', () => {
    const open = mountDrawer({ open: true })
    expect(open.find('.preview-backdrop').exists()).toBe(true)

    const closed = mountDrawer({ open: false })
    expect(closed.find('.preview-backdrop').exists()).toBe(false)
  })

  it('emits close when backdrop clicked', async () => {
    const wrapper = mountDrawer()
    await wrapper.find('.preview-backdrop').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('emits close when X button clicked', async () => {
    const wrapper = mountDrawer()
    await wrapper.find('.close-btn').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  /* ─── Metadata ─── */

  it('shows filename as title', () => {
    const wrapper = mountDrawer()
    expect(wrapper.find('.preview-title').text()).toBe('report.pdf')
  })

  it('shows file type tag', () => {
    const wrapper = mountDrawer()
    expect(wrapper.find('.tag').text()).toBe('PDF Document')
  })

  it('shows created date', () => {
    const wrapper = mountDrawer()
    const cells = wrapper.findAll('.meta-cell')
    const cell = cells.find((c) => c.text().includes('Created'))
    expect(cell.text()).toContain('2025-03-12')
  })

  it('shows file size', () => {
    const wrapper = mountDrawer()
    const cells = wrapper.findAll('.meta-cell')
    const cell = cells.find((c) => c.text().includes('File Size'))
    expect(cell.text()).toContain('204800')
  })

  it('shows format in metadata', () => {
    const wrapper = mountDrawer()
    const cells = wrapper.findAll('.meta-cell')
    const cell = cells.find((c) => c.text().includes('Format'))
    expect(cell.text()).toContain('PDF Document')
  })

  it('shows security class in metadata', () => {
    const wrapper = mountDrawer()
    const cells = wrapper.findAll('.meta-cell')
    const cell = cells.find((c) => c.text().includes('Security Class'))
    expect(cell.text()).toContain('Internal')
  })

  /* ─── Security edit ─── */

  describe('classification editing', () => {
    it('hides edit button for regular users', () => {
      mockHasRole.mockReturnValue(false)
      const wrapper = mountDrawer()
      expect(wrapper.find('.edit-btn').exists()).toBe(false)
    })

    it('shows edit button for admin', () => {
      mockHasRole.mockReturnValue(true)
      const wrapper = mountDrawer()
      expect(wrapper.find('.edit-btn').exists()).toBe(true)
    })

    it('checks the admin role specifically', () => {
      mockHasRole.mockReturnValue(true)
      mountDrawer()
      expect(mockHasRole).toHaveBeenCalledWith('admin')
    })

    it('opens editor on edit click', async () => {
      mockHasRole.mockReturnValue(true)
      const wrapper = mountDrawer()

      expect(wrapper.find('.mock-editor').exists()).toBe(false)
      await wrapper.find('.edit-btn').trigger('click')
      expect(wrapper.find('.mock-editor').exists()).toBe(true)
    })

    it('closes editor on cancel', async () => {
      mockHasRole.mockReturnValue(true)
      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      expect(wrapper.find('.mock-editor').exists()).toBe(true)

      await wrapper.find('.cancel-btn').trigger('click')
      await nextTick()
      expect(wrapper.find('.mock-editor').exists()).toBe(false)
    })

    it('saves classification via authFetch POST', async () => {
      mockHasRole.mockReturnValue(true)
      mockAuthFetch.mockResolvedValue({ ok: true })

      const wrapper = mountDrawer()
      await wrapper.find('.edit-btn').trigger('click')
      await wrapper.find('.save-btn').trigger('click')
      await flushPromises()

      expect(mockAuthFetch).toHaveBeenCalledTimes(1)
      const [url, opts] = mockAuthFetch.mock.calls[0]
      expect(url).toBe('/api/stochastic-analyzer/classification')
      expect(opts.method).toBe('POST')

      const body = JSON.parse(opts.body)
      expect(body.unique_pointer).toBe('ptr-abc-123')
      expect(body.security_class).toBe('Confidential')
    })

    it('updates local security level after successful save', async () => {
      mockHasRole.mockReturnValue(true)
      mockAuthFetch.mockResolvedValue({ ok: true })

      const wrapper = mountDrawer()
      await wrapper.find('.edit-btn').trigger('click')
      await wrapper.find('.save-btn').trigger('click')
      await flushPromises()

      const cell = wrapper.findAll('.meta-cell').find((c) => c.text().includes('Security Class'))
      expect(cell.text()).toContain('Confidential')
    })

    it('emits update-security after successful save', async () => {
      mockHasRole.mockReturnValue(true)
      mockAuthFetch.mockResolvedValue({ ok: true })

      const wrapper = mountDrawer()
      await wrapper.find('.edit-btn').trigger('click')
      await wrapper.find('.save-btn').trigger('click')
      await flushPromises()

      expect(wrapper.emitted('update-security')).toHaveLength(1)
      expect(wrapper.emitted('update-security')[0][0]).toEqual({
        uniquePointer: 'ptr-abc-123',
        security_class: 'Confidential'
      })
    })

    it('shows error notification when save fails (non-ok response)', async () => {
      mockHasRole.mockReturnValue(true)
      mockAuthFetch.mockResolvedValue({ ok: false, status: 403 })

      const wrapper = mountDrawer()
      await wrapper.find('.edit-btn').trigger('click')
      await wrapper.find('.save-btn').trigger('click')
      await flushPromises()

      const notif = wrapper.find('.notification-error')
      expect(notif.exists()).toBe(true)
      expect(notif.text()).toContain('Update failed')
    })

    it('shows error notification on network error', async () => {
      mockHasRole.mockReturnValue(true)
      mockAuthFetch.mockRejectedValue(new Error('timeout'))

      const wrapper = mountDrawer()
      await wrapper.find('.edit-btn').trigger('click')
      await wrapper.find('.save-btn').trigger('click')
      await flushPromises()

      const notif = wrapper.find('.notification-error')
      expect(notif.exists()).toBe(true)
      expect(notif.text()).toContain('timeout')
    })

    it('shows success notification after save', async () => {
      mockHasRole.mockReturnValue(true)
      mockAuthFetch.mockResolvedValue({ ok: true })

      const wrapper = mountDrawer()
      await wrapper.find('.edit-btn').trigger('click')
      await wrapper.find('.save-btn').trigger('click')
      await flushPromises()

      const notif = wrapper.find('.notification-success')
      expect(notif.exists()).toBe(true)
      expect(notif.text()).toContain('updated successfully')
    })

    it('closes editor after successful save', async () => {
      mockHasRole.mockReturnValue(true)
      mockAuthFetch.mockResolvedValue({ ok: true })

      const wrapper = mountDrawer()
      await wrapper.find('.edit-btn').trigger('click')
      await wrapper.find('.save-btn').trigger('click')
      await flushPromises()

      expect(wrapper.find('.mock-editor').exists()).toBe(false)
    })
  })

  /* ─── AI Summary ─── */

  it('shows generate summary button when no summary', () => {
    const wrapper = mountDrawer()
    const btn = wrapper.find('.summary-cell-button')
    expect(btn.text()).toContain('Generate AI Summary')
  })

  /* ─── Similarity / Rerank ─── */

  it('shows find similar files button when no rerank results', () => {
    const wrapper = mountDrawer()
    const btns = wrapper.findAll('.summary-cell-button')
    const btn = btns.find((b) => b.text().includes('Find Similar Files'))
    expect(btn).toBeTruthy()
  })

  /* ─── Footer ─── */

  it('renders open-in link when previewLink exists', () => {
    const wrapper = mountDrawer()
    const link = wrapper.find('.open-file-btn')
    expect(link.attributes('href')).toBe('https://example.com/report.pdf')
    expect(link.text()).toContain('Open file in SharePoint')
  })

  it('shows copy reference when no link but unique pointer exists', async () => {
    mockMetadata.previewLink.value = ''
    mockMetadata.uniquePointer.value = 'ptr-abc-123'

    const wrapper = mountDrawer()
    await nextTick()

    expect(wrapper.find('.file-reference-card').exists()).toBe(true)
    expect(wrapper.find('.file-reference-value').text()).toBe('ptr-abc-123')
    expect(wrapper.find('.copy-reference-btn').exists()).toBe(true)
  })

  it('shows disabled button when no link and no pointer', async () => {
    mockMetadata.previewLink.value = ''
    mockMetadata.uniquePointer.value = ''

    const wrapper = mountDrawer()
    await nextTick()

    const btn = wrapper.find('.open-file-btn')
    expect(btn.attributes('disabled')).toBeDefined()
    expect(btn.text()).toContain('No file reference available')
  })

  /* ─── State reset on file switch ─── */

  it('hides editor when selectedFile changes', async () => {
    mockHasRole.mockReturnValue(true)
    const wrapper = mountDrawer()

    await wrapper.find('.edit-btn').trigger('click')
    expect(wrapper.find('.mock-editor').exists()).toBe(true)

    await wrapper.setProps({ selectedFile: 'other.txt' })
    await nextTick()
    expect(wrapper.find('.mock-editor').exists()).toBe(false)
  })

  /*it('hides notification when selectedFile changes', async () => {
    mockHasRole.mockReturnValue(true)
    mockAuthFetch.mockResolvedValue({ ok: true })

    const wrapper = mountDrawer()
    await wrapper.find('.edit-btn').trigger('click')
    await wrapper.find('.save-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.notification').exists()).toBe(true)

    await wrapper.setProps({ selectedFile: 'other.txt' })
    await flushPromises() // Wait for any async state updates
    await nextTick() // Sometimes one tick isn't enough to clear notifications
    expect(wrapper.find('.notification').exists()).toBe(false)
  }) */
})
