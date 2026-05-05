
/* SearchPreviewDrawer Tests */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import SearchPreviewDrawer from '@/components/SearchPreviewDrawer.vue'

/* ──────────────────────────────────────────────
   Mocks — must use real ref() so Vue auto-unwraps
   in templates (plain { value: x } won't unwrap)
   ────────────────────────────────────────────── */

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

vi.mock('@/composables/aiRerank', () => {
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

const mockSaveClassification = vi.fn()
vi.mock('@/utils/api', () => ({
  saveClassification: (...args) => mockSaveClassification(...args)
}))

/* ──────────────────────────────────────────────
   Helpers
   ────────────────────────────────────────────── */

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

const iconStubs = {
  X: true,
  StarsIcon: true,
  CalendarDays: true,
  HardDrive: true,
  FileType2: true,
  ExternalLink: true,
  ShieldCheck: true,
  Pencil: true,
  CheckCircle: true,
  AlertCircle: true
}

const mountComponent = (props = {}) =>
  mount(SearchPreviewDrawer, {
    props: { ...defaultProps, ...props },
    global: {
      stubs: {
        ...iconStubs,
        ClassificationEditor: {
          template:
            '<div class="mock-editor"><button class="save-btn" @click="$emit(\'save\', \'Confidential\')">Save</button><button class="cancel-btn" @click="$emit(\'cancel\')">Cancel</button></div>',
          props: ['currentLevel'],
          methods: { resetSaving: vi.fn() }
        },
        Transition: false
      },
      mocks: {
        $router: { push: vi.fn() }
      }
    }
  })

/* ═══════════════════════════════════════════════ */

describe('SearchPreviewDrawer.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockHasRole.mockReturnValue(false)
  })

  /* ─── Open / Close ─── */

  describe('open/close', () => {
    it('has "open" class when open prop is true', () => {
      const wrapper = mountComponent({ open: true })
      expect(wrapper.find('.preview-drawer').classes()).toContain('open')
    })

    it('does not have "open" class when open is false', () => {
      const wrapper = mountComponent({ open: false })
      expect(wrapper.find('.preview-drawer').classes()).not.toContain('open')
    })

    it('renders backdrop when open', () => {
      const wrapper = mountComponent({ open: true })
      expect(wrapper.find('.preview-backdrop').exists()).toBe(true)
    })

    it('does not render backdrop when closed', () => {
      const wrapper = mountComponent({ open: false })
      expect(wrapper.find('.preview-backdrop').exists()).toBe(false)
    })

    it('emits "close" when backdrop is clicked', async () => {
      const wrapper = mountComponent({ open: true })
      await wrapper.find('.preview-backdrop').trigger('click')

      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('emits "close" when X button is clicked', async () => {
      const wrapper = mountComponent({ open: true })
      await wrapper.find('.close-btn').trigger('click')

      expect(wrapper.emitted('close')).toHaveLength(1)
    })
  })

  /* ─── Metadata display ─── */

  describe('metadata display', () => {
    it('displays the preview title', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('.preview-title').text()).toBe('report.pdf')
    })

    it('displays the file description tag', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('.tag').text()).toBe('PDF Document')
    })

    it('displays created date in metadata grid', () => {
      const wrapper = mountComponent()
      const cells = wrapper.findAll('.meta-cell')
      const createdCell = cells.find((c) => c.text().includes('Created'))
      expect(createdCell.text()).toContain('2025-03-12')
    })

    it('displays file size in metadata grid', () => {
      const wrapper = mountComponent()
      const cells = wrapper.findAll('.meta-cell')
      const sizeCell = cells.find((c) => c.text().includes('File Size'))
      expect(sizeCell.text()).toContain('204800')
    })

    it('displays security class in metadata grid', () => {
      const wrapper = mountComponent()
      const cells = wrapper.findAll('.meta-cell')
      const securityCell = cells.find((c) => c.text().includes('Security Class'))
      expect(securityCell.text()).toContain('Internal')
    })
  })

  /* ─── Security classification section ─── */

  describe('security classification', () => {
    it('shows the classification badge', () => {
      const wrapper = mountComponent()
      const badge = wrapper.find('.classification-badge')
      expect(badge.text()).toBe('Internal')
      expect(badge.classes()).toContain('badge-internal')
    })

    it('does not show edit button for non-admin users', () => {
      mockHasRole.mockReturnValue(false)
      const wrapper = mountComponent()
      expect(wrapper.find('.edit-btn').exists()).toBe(false)
    })

    it('shows edit button for admin users', () => {
      mockHasRole.mockReturnValue(true)
      const wrapper = mountComponent()
      expect(wrapper.find('.edit-btn').exists()).toBe(true)
    })

    it('opens classification editor when edit is clicked', async () => {
      mockHasRole.mockReturnValue(true)
      const wrapper = mountComponent()

      await wrapper.find('.edit-btn').trigger('click')
      expect(wrapper.find('.mock-editor').exists()).toBe(true)
    })
  })

  /* ─── Footer link ─── */

  describe('footer', () => {
    it('renders "Open file in" link when previewLink exists', () => {
      const wrapper = mountComponent()
      const link = wrapper.find('.open-file-btn')
      expect(link.attributes('href')).toBe('https://example.com/report.pdf')
      expect(link.text()).toContain('Open file in SharePoint')
    })
  })

  /* ─── AI Summary section ─── */

  describe('AI summary section', () => {
    it('shows "Generate AI Summary" button when no summary exists', () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.summary-cell-button')
      expect(btn.text()).toContain('Generate AI Summary')
    })
  })

  /* ─── Rerank / Similarity section ─── */

  describe('similarity section', () => {
    it('shows "Find Similar Files" button when no rerank results exist', () => {
      const wrapper = mountComponent()
      const buttons = wrapper.findAll('.summary-cell-button')
      const rerankBtn = buttons.find((b) => b.text().includes('Find Similar Files'))
      expect(rerankBtn).toBeTruthy()
    })
  })

  /* ─── State reset on file change ─── */

  describe('state reset', () => {
    it('hides classification editor when selectedFile changes', async () => {
      mockHasRole.mockReturnValue(true)
      const wrapper = mountComponent()

      // Open editor
      await wrapper.find('.edit-btn').trigger('click')
      expect(wrapper.find('.mock-editor').exists()).toBe(true)

      // Change file
      await wrapper.setProps({ selectedFile: 'other-file.txt' })
      await nextTick()
      expect(wrapper.find('.mock-editor').exists()).toBe(false)
    })

    it('hides notification when selectedFile changes', async () => {
      const wrapper = mountComponent()
      // Notification is hidden by default, should remain hidden
      await wrapper.setProps({ selectedFile: 'other-file.txt' })
      await nextTick()
      expect(wrapper.find('.notification').exists()).toBe(false)
    })
  })
})
