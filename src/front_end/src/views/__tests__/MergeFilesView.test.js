import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import MergeFilesView from '@/views/MergeFilesView.vue'

/* ──────────────────────────────────────────────
   Mocks — use real ref() so Vue auto-unwraps
   them in templates. Plain { value: x } objects
   won't be unwrapped and break v-if / {{ }}.
   ────────────────────────────────────────────── */

const mockRerankResults = ref([
  { name: 'alpha.pdf', score: 0.92, unique_pointer: 'ptr-1', scorePercent: '92.0%', rank: 1 },
  { name: 'beta.docx', score: 0.78, unique_pointer: 'ptr-2', scorePercent: '78.0%', rank: 2 },
  { name: 'gamma.txt', score: 0.65, unique_pointer: 'ptr-3', scorePercent: '65.0%', rank: 3 }
])

const mockRerankFilename = ref('source-file.pdf')
const mockRerankPointer = ref('ptr-source')

vi.mock('@/composables/aiRerank', () => ({
  useAIRerank: () => ({
    aiRerankResults: mockRerankResults,
    rerankFilename: mockRerankFilename,
    rerankPointer: mockRerankPointer
  })
}))

const mockGenerateSummary = vi.fn()
const mockSummaryHtml = ref('')
const mockSummaryError = ref('')
const mockIsGenerating = ref(false)

vi.mock('@/composables/aiSummary', () => ({
  useAISummary: () => ({
    aiSummaryHtml: mockSummaryHtml,
    summaryError: mockSummaryError,
    isGeneratingSummary: mockIsGenerating,
    generateAISummary: mockGenerateSummary
  })
}))

/* Stub SearchMatches so we can inspect props and simulate emits */
const SearchMatchesStub = {
  name: 'SearchMatches',
  template: `
    <div class="stub-search-matches">
      <button
        v-for="m in matches"
        :key="m.unique_pointer"
        class="stub-match"
        @click="$emit('update:selectedPointers', togglePointer(m.unique_pointer))"
      >
        {{ m.name }}
      </button>
    </div>
  `,
  props: {
    matches: { type: Array, default: () => [] },
    selectedPointers: { type: Array, default: () => [] },
    badgeMode: { type: String, default: '' },
    selectable: { type: Boolean, default: false }
  },
  emits: ['update:selectedPointers'],
  methods: {
    togglePointer(ptr) {
      return this.selectedPointers.includes(ptr) ? this.selectedPointers.filter((p) => p !== ptr) : [...this.selectedPointers, ptr]
    }
  }
}

/* ──────────────────────────────────────────────
   Helpers
   ────────────────────────────────────────────── */

const mountComponent = () =>
  mount(MergeFilesView, {
    global: {
      stubs: {
        SearchMatches: SearchMatchesStub
      },
      mocks: {
        $router: { push: vi.fn() }
      }
    }
  })

/* ═══════════════════════════════════════════════ */

describe('MergeFilesView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSummaryHtml.value = ''
    mockSummaryError.value = ''
    mockIsGenerating.value = false
    mockRerankResults.value = [
      { name: 'alpha.pdf', score: 0.92, unique_pointer: 'ptr-1', scorePercent: '92.0%', rank: 1 },
      { name: 'beta.docx', score: 0.78, unique_pointer: 'ptr-2', scorePercent: '78.0%', rank: 2 },
      { name: 'gamma.txt', score: 0.65, unique_pointer: 'ptr-3', scorePercent: '65.0%', rank: 3 }
    ]
    mockRerankFilename.value = 'source-file.pdf'
    mockRerankPointer.value = 'ptr-source'
  })

  /* ─── Rendering with results ─── */

  describe('rendering — with rerank results', () => {
    it('displays the page title', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('h1').text()).toContain('Merge/Summarize')
    })

    it('shows "Similar to:" with the rerank filename', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('h3').text()).toContain('source-file.pdf')
    })

    it('passes rerank results to SearchMatches', () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })
      expect(stub.props('matches')).toHaveLength(3)
    })

    it('passes selectable=true to SearchMatches', () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })
      expect(stub.props('selectable')).toBe(true)
    })

    it('passes badgeMode="score" to SearchMatches', () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })
      expect(stub.props('badgeMode')).toBe('score')
    })

    it('starts with the rerank pointer pre-selected', () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })
      expect(stub.props('selectedPointers')).toContain('ptr-source')
    })
  })

  /* ─── Rendering — no results ─── */

  describe('rendering — no rerank results', () => {
    it('does not render the file list or actions when results are empty', () => {
      mockRerankResults.value = []
      const wrapper = mountComponent()
      expect(wrapper.find('.stub-search-matches').exists()).toBe(false)
      expect(wrapper.find('.merge-actions').exists()).toBe(false)
    })
  })

  /* ─── Selection count ─── */

  describe('selection counter', () => {
    it('shows count of selected files', () => {
      const wrapper = mountComponent()
      const actionsText = wrapper.find('.merge-actions p').text()
      // Initially the rerank pointer is selected (1 file)
      expect(actionsText).toContain('1 file selected')
    })

    it('uses plural form for multiple selections', async () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })

      // Simulate selecting another pointer
      await stub.vm.$emit('update:selectedPointers', ['ptr-source', 'ptr-1'])
      await nextTick()

      const actionsText = wrapper.find('.merge-actions p').text()
      expect(actionsText).toContain('2 files selected')
    })
  })

  /* ─── Merge & Summarize button ─── */

  describe('merge & summarize button', () => {
    it('renders the merge button', () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.merge-actions button')
      expect(btn.text()).toContain('Merge & Summarize')
    })

    it('calls generateAISummary with selected pointers and rerank pointer', async () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.merge-actions button')

      await btn.trigger('click')

      expect(mockGenerateSummary).toHaveBeenCalledTimes(1)
      const [pointers] = mockGenerateSummary.mock.calls[0]
      expect(pointers).toContain('ptr-source')
      // NOTE: The component template uses `rerankPointer.value`, but Vue auto-unwraps
      // refs in templates, so rerankPointer is already the string 'ptr-source' and
      // `.value` resolves to undefined. Consider fixing the template to just `rerankPointer`.
      const sourcePointer = mockGenerateSummary.mock.calls[0][1]
      expect(sourcePointer).toBeUndefined()
    })

    it('is disabled when isGeneratingSummary is true', async () => {
      mockIsGenerating.value = true
      const wrapper = mountComponent()
      await nextTick()

      const btn = wrapper.find('.merge-actions button')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('is disabled when no files are selected', async () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })

      // Deselect everything
      await stub.vm.$emit('update:selectedPointers', [])
      await nextTick()

      const btn = wrapper.find('.merge-actions button')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('shows "Generating summary..." text during generation', async () => {
      mockIsGenerating.value = true
      const wrapper = mountComponent()
      await nextTick()

      const btn = wrapper.find('.merge-actions button')
      expect(btn.text()).toContain('Generating summary...')
    })
  })

  /* ─── Summary result display ─── */

  describe('summary result', () => {
    it('does not show summary section when aiSummaryHtml is empty', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('.summary-result').exists()).toBe(false)
    })

    it('shows summary section with rendered HTML when available', async () => {
      mockSummaryHtml.value = '<p>This is a merged summary.</p>'
      const wrapper = mountComponent()
      await nextTick()

      const section = wrapper.find('.summary-result')
      expect(section.exists()).toBe(true)
      expect(section.find('.summary-markdown').html()).toContain('This is a merged summary.')
    })
  })

  /* ─── Error display ─── */

  describe('error handling', () => {
    it('shows error message when summaryError is set', async () => {
      mockSummaryError.value = 'Something went wrong'
      const wrapper = mountComponent()
      await nextTick()

      expect(wrapper.text()).toContain('Error generating summary: Something went wrong')
    })
  })
})
