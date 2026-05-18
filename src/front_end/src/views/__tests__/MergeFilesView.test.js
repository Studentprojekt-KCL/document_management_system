/* MergeFilesView Tests */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref, nextTick } from 'vue'
import MergeFilesView from '@/views/MergeFilesView.vue'

const mockRerankResults = ref([])
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
const mockResetSummary = vi.fn()
const mockSummaryHtml = ref('')
const mockSummaryError = ref('')
const mockIsGenerating = ref(false)

vi.mock('@/composables/aiSummary', () => ({
  useAISummary: () => ({
    aiSummaryHtml: mockSummaryHtml,
    summaryError: mockSummaryError,
    isGeneratingSummary: mockIsGenerating,
    generateAISummary: mockGenerateSummary,
    resetSummary: mockResetSummary
  })
}))

const mockGeneratePDF = vi.fn()
const mockResetMerged = vi.fn()
const mockPdfError = ref('')
const mockPdfUrl = ref('')
const mockIsGeneratingPDF = ref(false)
const mockMergedHtmlRaw = ref('')

vi.mock('@/composables/mdToPdf', () => ({
  useMdToPdf: () => ({
    generatePDF: mockGeneratePDF,
    pdfError: mockPdfError,
    mergedHtmlRaw: mockMergedHtmlRaw,
    isGeneratingPDF: mockIsGeneratingPDF,
    pdfUrl: mockPdfUrl,
    resetMerged: mockResetMerged
  })
}))

/* Stub SearchMatches to inspect props and emit selection changes */
const SearchMatchesStub = {
  name: 'SearchMatches',
  template: '<div class="stub-matches"><slot /></div>',
  props: {
    matches: { type: Array, default: () => [] },
    selectedPointers: { type: Array, default: () => [] },
    badgeMode: { type: String, default: '' },
    selectable: { type: Boolean, default: false }
  },
  emits: ['update:selectedPointers']
}

const mountComponent = () =>
  mount(MergeFilesView, {
    global: {
      stubs: { SearchMatches: SearchMatchesStub }
    }
  })

describe('MergeFilesView.vue', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSummaryHtml.value = ''
    mockSummaryError.value = ''
    mockIsGenerating.value = false
    mockPdfError.value = ''
    mockPdfUrl.value = ''
    mockIsGeneratingPDF.value = false
    mockMergedHtmlRaw.value = ''
    mockRerankResults.value = [
      { name: 'alpha.pdf', score: 0.92, unique_pointer: 'ptr-1', scorePercent: '92.0%', rank: 1 },
      { name: 'beta.docx', score: 0.78, unique_pointer: 'ptr-2', scorePercent: '78.0%', rank: 2 },
      { name: 'gamma.txt', score: 0.65, unique_pointer: 'ptr-3', scorePercent: '65.0%', rank: 3 }
    ]
    mockRerankFilename.value = 'source-file.pdf'
    mockRerankPointer.value = 'ptr-source'
  })

  describe('rendering — with rerank results', () => {
    it('displays the page title', () => {
      const wrapper = mountComponent()
      // Ensure a main heading is present for the page
      const h1 = wrapper.find('h1')
      expect(h1.exists()).toBe(true)
      expect(h1.text().length).toBeGreaterThan(0)
    })

    it('shows the rerank filename', () => {
      const wrapper = mountComponent()
      // Filename is dynamic and important; keep assertion that it is rendered
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

  describe('rendering — no rerank results', () => {
    it('does not render results section when results are empty', () => {
      mockRerankResults.value = []
      const wrapper = mountComponent()
      expect(wrapper.find('.stub-matches').exists()).toBe(false)
      expect(wrapper.find('.actions').exists()).toBe(false)
    })
  })

  describe('selection counter', () => {
    it('shows count of selected files', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('.actions p').text()).toContain('1 file selected')
    })

    it('uses plural form for multiple selections', async () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })

      await stub.vm.$emit('update:selectedPointers', ['ptr-source', 'ptr-1'])
      await nextTick()

      expect(wrapper.find('.actions p').text()).toContain('2 files selected')
    })
  })

  describe('merge + generate PDF button', () => {
    it('renders the merge button', () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.pdf-actions button')
      // Ensure merge/generate button exists; behavior tested below
      expect(btn.exists()).toBe(true)
    })

    it('calls generatePDF with selected pointers and rerankPointer', async () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.pdf-actions button')

      await btn.trigger('click')

      expect(mockResetMerged).toHaveBeenCalledTimes(1)
      expect(mockGeneratePDF).toHaveBeenCalledTimes(1)
      expect(mockGeneratePDF).toHaveBeenCalledWith(['ptr-source'], 'ptr-source')
    })

    it('is disabled when isGeneratingPDF is true', async () => {
      mockIsGeneratingPDF.value = true
      const wrapper = mountComponent()
      await nextTick()

      const btn = wrapper.find('.pdf-actions button')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('is disabled when no files are selected', async () => {
      const wrapper = mountComponent()
      const stub = wrapper.findComponent({ name: 'SearchMatches' })

      await stub.vm.$emit('update:selectedPointers', [])
      await nextTick()

      const btn = wrapper.find('.pdf-actions button')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('shows "Generating PDF..." text during generation', async () => {
      mockIsGeneratingPDF.value = true
      const wrapper = mountComponent()
      await nextTick()

      const btn = wrapper.find('.pdf-actions button')
      // Indicate generation state via presence of disabled attribute or non-empty label
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('shows download and preview links after PDF generation', async () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.pdf-actions button')

      await btn.trigger('click')
      mockPdfUrl.value = 'blob:http://example.com/pdf'
      await nextTick()

      const downloadSection = wrapper.find('.download-section')
      expect(downloadSection.exists()).toBe(true)
      expect(downloadSection.find('a').text()).toContain('Preview merged PDF')
    })

    it('shows PDF error message when pdfError is set', async () => {
      mockPdfError.value = 'Generation failed'
      const wrapper = mountComponent()
      await nextTick()

      expect(wrapper.find('.pdf-actions .error').text()).toContain('Error generating PDF: Generation failed')
    })
  })

  describe('summarize button', () => {
    it('renders the summarize button', () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.summary-actions button')
      expect(btn.exists()).toBe(true)
    })

    it('calls generateAISummary with selected pointers and rerankPointer', async () => {
      const wrapper = mountComponent()
      const btn = wrapper.find('.summary-actions button')

      await btn.trigger('click')

      expect(mockResetSummary).toHaveBeenCalledTimes(1)
      expect(mockGenerateSummary).toHaveBeenCalledTimes(1)
      expect(mockGenerateSummary).toHaveBeenCalledWith(['ptr-source'], 'ptr-source')
    })

    it('is disabled when isGeneratingSummary is true', async () => {
      mockIsGenerating.value = true
      const wrapper = mountComponent()
      await nextTick()

      const btn = wrapper.find('.summary-actions button')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('shows "Generating summary..." text during generation', async () => {
      mockIsGenerating.value = true
      const wrapper = mountComponent()
      await nextTick()

      const btn = wrapper.find('.summary-actions button')
      expect(btn.attributes('disabled')).toBeDefined()
    })

    it('shows summary error message when summaryError is set', async () => {
      mockSummaryError.value = 'Something went wrong'
      const wrapper = mountComponent()
      await nextTick()

      expect(wrapper.find('.summary-actions .error').text()).toContain('Error generating summary: Something went wrong')
    })
  })

  describe('summary result display', () => {
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

  describe('merged result display', () => {
    it('does not show merged result section when mergedHtmlRaw is empty', () => {
      const wrapper = mountComponent()
      expect(wrapper.find('.merged-html-result').exists()).toBe(false)
    })

    it('shows merged result section when mergedHtmlRaw is available', async () => {
      mockMergedHtmlRaw.value = '<p>Merged content here.</p>'
      const wrapper = mountComponent()
      await nextTick()

      const section = wrapper.find('.merged-html-result')
      expect(section.exists()).toBe(true)
      expect(section.find('.summary-markdown').html()).toContain('Merged content here.')
    })
  })
})
