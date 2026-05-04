import { computed, ref } from 'vue'
import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'

export function useMdToPdf(props = {}) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  /* PDF generation state */
  const mergedMarkdown = ref('')
  const mergedHtmlRaw = ref('')
  const pdfError = ref('')
  const isGeneratingPDF = ref(false)

  const mergedHtml = computed(() => {
    if (!uniquePointer.value) {
      return mergedHtmlRaw.value
    }

    return mergedMarkdown.value && mergedHtmlRaw.value ? mergedHtmlRaw.value : ''
  })

  /* /merge returns markdown, then markdown is sent to /md-to-pdf to receive the PDF blob. */
  const generatePDF = async (pointers = [], sourcePointer = '') => {
    const filesToMerge = pointers && pointers.length > 0 ? pointers : uniquePointer.value ? [uniquePointer.value] : []
    const requestPointers = [...new Set([...filesToMerge, sourcePointer].filter((p) => p?.trim()))]

    if (!requestPointers.length) {
      pdfError.value = 'No valid pointer provided for PDF generation.'
      return
    }

    isGeneratingPDF.value = true
    pdfError.value = ''
    mergedHtmlRaw.value = ''
    mergedMarkdown.value = ''

    try {
      const mergeResponse = await authFetch(API_PATHS.merge, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pointers: requestPointers })
      })
      console.log('Pointers sent for merge:', requestPointers) // Debug log for pointers sent to merge

      if (!mergeResponse.ok) {
        throw new Error(`Merge request failed (${mergeResponse.status})`)
      }

      const mergeContentType = mergeResponse.headers.get('content-type') || ''
      let markdownText = ''

      if (mergeContentType.includes('application/json')) {
        const data = await mergeResponse.json()
        markdownText = typeof data.summary === 'string' ? data.summary : JSON.stringify(data)
      } else {
        markdownText = await mergeResponse.text()
      }

      mergedMarkdown.value = markdownText
      mergedHtmlRaw.value = markdownText
      console.log('Merged Markdown:', markdownText) // Debug log for merged markdown

      const pdfResponse = await authFetch(API_PATHS.mdToPDF, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ summary: mergedHtml })
      })

      if (!pdfResponse.ok) {
        const errorBody = await pdfResponse.text()
        throw new Error(`PDF generation request failed (${pdfResponse.status}): ${errorBody}`)
      }

      console.log('PDF generation response received') // Debug log for PDF response

      const blob = await pdfResponse.blob()
      const url = window.URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = url
      a.download = 'converted.pdf'
      document.body.appendChild(a)
      a.click()
      a.remove()

      window.URL.revokeObjectURL(url)
    } catch (error) {
      pdfError.value = error.message || 'An error occurred while generating the PDF.'
    } finally {
      isGeneratingPDF.value = false
    }
  }

  return { generatePDF, mergedMarkdown, mergedHtml, pdfError, isGeneratingPDF }
}
