import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

/* ── Mock dependencies ── */

/* Mock api.js */
const mockAuthFetch = vi.hoisted(() => vi.fn())
vi.mock('@/utils/api', () => ({
  authFetch: mockAuthFetch,
  API_PATHS: {
    classification: '/api/search_engine/classification',
    summarize: '/api/stochastic-analyzer/summarize'
  },
  saveClassification: vi.fn()
}))

/* Mock useSearchMetadata */
vi.mock('@/composables/useSearchMetadata', () => {
  const { computed } = require('vue')
  return {
    useSearchMetadata: () => ({
      previewTitle: computed(() => 'test-file.pdf'),
      previewFileDescription: computed(() => 'PDF Document'),
      previewFileExtension: computed(() => '.pdf'),
      sourceSystem: computed(() => 'GitLab'),
      previewCreatedAt: computed(() => '2026-04-15'),
      previewSize: computed(() => '44982'),
      previewLink: computed(() => 'https://gitlab.com/file'),
      previewSecurityClass: computed(() => 'Public'),
      uniquePointer: computed(() => 'https://gitlab.com/api/v4/projects/1/files/test.pdf')
    }),
    resolveFilename: () => 'test-file.pdf',
    resolveSecurityClass: (entry) => entry?.security_class || ''
  }
})

/* Mock useAISummary */
vi.mock('@/composables/aiSummary', () => {
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

/* Mock auth */
vi.mock('@/utils/auth', () => ({
  hasRole: vi.fn(() => true),
  isLoggedIn: vi.fn(() => true)
}))

/* Mock ClassificationEditor */
const MockClassificationEditor = {
  name: 'ClassificationEditor',
  template: '<div class="mock-editor"></div>',
  props: ['visible', 'currentLevel'],
  emits: ['save', 'cancel'],
  methods: {
    resetSaving() {}
  }
}

vi.mock('@/components/ClassificationEditor.vue', () => ({
  default: MockClassificationEditor
}))

import SearchPreviewDrawer from '@/components/SearchPreviewDrawer.vue'
import { hasRole } from '@/utils/auth'

describe('SearchPreviewDrawer', () => {
  const defaultProps = {
    open: true,
    selectedFile: 'test-file.pdf',
    selectedMatch: {
      name: 'test-file.pdf',
      unique_pointer: 'https://gitlab.com/api/v4/projects/1/files/test.pdf',
      security_class: 'Public',
      source_system: 'GitLab',
      size: '44982',
      last_edit_date: '2026-04-15T14:30:00.000Z',
      clickable_url: 'https://gitlab.com/file'
    },
    matches: []
  }

  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.setItem('access_token', 'test-token')
    sessionStorage.setItem('access_token', 'test-token')
    vi.mocked(hasRole).mockReturnValue(true)
  })

  afterEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    vi.restoreAllMocks()
  })

  const mountDrawer = (props = {}) => {
    return mount(SearchPreviewDrawer, {
      props: {
        ...defaultProps,
        ...props
      },
      global: {
        stubs: {
          ClassificationEditor: MockClassificationEditor
        }
      }
    })
  }

  /* ── Rendering ── */
  describe('rendering', () => {
    it('renders the drawer when open is true', () => {
      const wrapper = mountDrawer()
      expect(wrapper.find('.preview-drawer').exists()).toBe(true)
      expect(wrapper.find('.preview-drawer').classes()).toContain('open')
    })

    it('drawer exists but is not open when open is false', () => {
      const wrapper = mountDrawer({ open: false })
      expect(wrapper.find('.preview-drawer').exists()).toBe(true)
      expect(wrapper.find('.preview-drawer').classes()).not.toContain('open')
    })

    it('shows the backdrop when open', () => {
      const wrapper = mountDrawer()
      expect(wrapper.find('.preview-backdrop').exists()).toBe(true)
    })

    it('hides the backdrop when closed', () => {
      const wrapper = mountDrawer({ open: false })
      expect(wrapper.find('.preview-backdrop').exists()).toBe(false)
    })

    it('displays the document title', () => {
      const wrapper = mountDrawer()
      expect(wrapper.find('.preview-title').text()).toBe('test-file.pdf')
    })

    it('displays the document type tag', () => {
      const wrapper = mountDrawer()
      expect(wrapper.find('.tag').text()).toBe('PDF Document')
    })

    it('displays the header text', () => {
      const wrapper = mountDrawer()
      expect(wrapper.find('.panel-kicker').text()).toBe('DOCUMENT INTELLIGENCE')
    })
  })

  /* ── Metadata section ── */
  describe('metadata', () => {
    it('displays created date', () => {
      const wrapper = mountDrawer()
      const cells = wrapper.findAll('.meta-cell')
      const createdCell = cells.find((c) => c.find('span').text() === 'Created')
      expect(createdCell).toBeTruthy()
    })

    it('displays file size', () => {
      const wrapper = mountDrawer()
      const cells = wrapper.findAll('.meta-cell')
      const sizeCell = cells.find((c) => c.find('span').text() === 'File Size')
      expect(sizeCell).toBeTruthy()
    })

    it('displays format', () => {
      const wrapper = mountDrawer()
      const cells = wrapper.findAll('.meta-cell')
      const formatCell = cells.find((c) => c.find('span').text() === 'Format')
      expect(formatCell).toBeTruthy()
    })

    it('displays security class in metadata grid', () => {
      const wrapper = mountDrawer()
      const cells = wrapper.findAll('.meta-cell')
      const securityCell = cells.find((c) => c.find('span').text() === 'Security Class')
      expect(securityCell).toBeTruthy()
    })
  })

  /* ── Security classification section ── */
  describe('security classification', () => {
    it('shows the classification badge', () => {
      const wrapper = mountDrawer()
      expect(wrapper.find('.classification-badge').exists()).toBe(true)
    })

    it('shows Edit button for admin users', () => {
      vi.mocked(hasRole).mockReturnValue(true)
      const wrapper = mountDrawer()
      expect(wrapper.find('.edit-btn').exists()).toBe(true)
    })

    it('hides Edit button for non-admin users', () => {
      vi.mocked(hasRole).mockReturnValue(false)
      const wrapper = mountDrawer()
      expect(wrapper.find('.edit-btn').exists()).toBe(false)
    })

    it('opens classification editor when Edit is clicked', async () => {
      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)
      expect(editor.exists()).toBe(true)
      expect(editor.props('visible')).toBe(true)
    })
  })

  /* ── Close behavior ── */
  describe('close', () => {
    it('emits close when close button is clicked', async () => {
      const wrapper = mountDrawer()

      await wrapper.find('.close-btn').trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('emits close when backdrop is clicked', async () => {
      const wrapper = mountDrawer()

      await wrapper.find('.preview-backdrop').trigger('click')

      expect(wrapper.emitted('close')).toBeTruthy()
    })
  })

  /* ── Open file link ── */
  describe('open file link', () => {
    it('shows the open file button with source system name', () => {
      const wrapper = mountDrawer()
      const link = wrapper.find('.open-file-btn')
      expect(link.exists()).toBe(true)
      expect(link.text()).toContain('Open file')
    })

    it('renders as a link when previewLink exists', () => {
      const wrapper = mountDrawer()
      const link = wrapper.find('a.open-file-btn')
      expect(link.exists()).toBe(true)
      expect(link.attributes('href')).toBe('https://gitlab.com/file')
      expect(link.attributes('target')).toBe('_blank')
    })
  })

  /* ── AI Summary section ── */
  describe('AI summary', () => {
    it('shows the Generate AI Summary button', () => {
      const wrapper = mountDrawer()
      expect(wrapper.find('.summary-cell-button').exists()).toBe(true)
      expect(wrapper.find('.summary-cell-button').text()).toContain('Generate AI Summary')
    })
  })

  /* ── Classification save flow ── */
  describe('classification save', () => {
    it('calls authFetch with correct endpoint on save', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ edited: true })
      })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)
      editor.vm.$emit('save', 'Confidential')
      await flushPromises()

      expect(mockAuthFetch).toHaveBeenCalledWith(
        '/api/search_engine/classification',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: expect.any(String)
        })
      )
    })

    it('shows success toast after successful save', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ edited: true })
      })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)
      editor.vm.$emit('save', 'Confidential')
      await flushPromises()

      const toast = wrapper.find('.toast-success')
      expect(toast.exists()).toBe(true)
      expect(toast.text()).toContain('updated successfully')
    })

    it('shows error toast on failed save', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: false,
        status: 500
      })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)
      editor.vm.$emit('save', 'Confidential')
      await flushPromises()

      const toast = wrapper.find('.toast-error')
      expect(toast.exists()).toBe(true)
      expect(toast.text()).toContain('Update failed')
    })

    it('shows error toast on network error', async () => {
      mockAuthFetch.mockRejectedValue(new Error('Network error'))

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)
      editor.vm.$emit('save', 'Confidential')
      await flushPromises()

      const toast = wrapper.find('.toast-error')
      expect(toast.exists()).toBe(true)
    })

    it('closes editor after successful save', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ edited: true })
      })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)
      editor.vm.$emit('save', 'Public')
      await flushPromises()

      expect(editor.props('visible')).toBe(false)
    })
  })

  /* ── State reset on document change ── */
  describe('state reset', () => {
    it('closes editor when selectedFile changes', async () => {
      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      await wrapper.setProps({ selectedFile: 'other-file.md' })
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)
      expect(editor.props('visible')).toBe(false)
    })

    it('hides toast when document changes', async () => {
      mockAuthFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ edited: true })
      })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()
      const editor = wrapper.findComponent(MockClassificationEditor)
      editor.vm.$emit('save', 'Public')
      await flushPromises()

      expect(wrapper.find('.toast-success').exists()).toBe(true)

      await wrapper.setProps({ selectedFile: 'different-file.md' })
      await flushPromises()

      expect(wrapper.find('.toast-success').exists()).toBe(false)
    })
  })
})
