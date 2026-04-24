import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

/* ── Mock dependencies ── */
const mockAuthFetch = vi.hoisted(() => vi.fn())

vi.mock('@/utils/api', () => ({
  authFetch: mockAuthFetch,
  API_PATHS: {
    classification: '/api/search_engine/classification',
    summarize: '/api/stochastic-analyzer/summarize'
  },
  saveClassification: vi.fn()
}))

import { saveClassification } from '@/utils/api'

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

vi.mock('@/utils/auth', () => ({
  hasRole: vi.fn(() => true),
  isLoggedIn: vi.fn(() => true)
}))

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
    vi.mocked(hasRole).mockReturnValue(true)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  const mountDrawer = (props = {}) =>
    mount(SearchPreviewDrawer, {
      props: { ...defaultProps, ...props },
      global: {
        stubs: {
          ClassificationEditor: MockClassificationEditor
        }
      }
    })

  /* ── Classification save flow ── */
  describe('classification save', () => {
    it('calls saveClassification with correct args', async () => {
      vi.mocked(saveClassification).mockResolvedValue({ edited: true })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)

      editor.vm.$emit('save', 'Confidential')
      await flushPromises()

      expect(saveClassification).toHaveBeenCalledWith(
        'https://gitlab.com/api/v4/projects/1/files/test.pdf',
        'Confidential'
      )
    })

    it('shows success notification after successful save', async () => {
      vi.mocked(saveClassification).mockResolvedValue({ edited: true })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)

      editor.vm.$emit('save', 'Confidential')
      await flushPromises()

      expect(wrapper.find('.notification-success').exists()).toBe(true)
    })

    it('shows error notification on failed save', async () => {
      vi.mocked(saveClassification).mockRejectedValue(new Error('fail'))

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)

      editor.vm.$emit('save', 'Confidential')
      await flushPromises()

      expect(wrapper.find('.notification-error').exists()).toBe(true)
    })

    it('closes editor after successful save', async () => {
      vi.mocked(saveClassification).mockResolvedValue({ edited: true })

      const wrapper = mountDrawer()

      await wrapper.find('.edit-btn').trigger('click')
      await nextTick()

      const editor = wrapper.findComponent(MockClassificationEditor)

      editor.vm.$emit('save', 'Public')
      await flushPromises()

      expect(wrapper.find('.notification-success').exists()).toBe(true)
    })
  })
})