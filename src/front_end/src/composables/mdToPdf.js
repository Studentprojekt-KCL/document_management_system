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
  const pdfUrl = ref('')
  const isGeneratingPDF = ref(false)

  const mergedHtml = computed(() => {
    if (!uniquePointer.value) {
      return mergedHtmlRaw.value
    }

    return mergedMarkdown.value && mergedHtmlRaw.value ? mergedHtmlRaw.value : ''
  })

  /* Merge files part */
  const mergeFiles = async (pointers = [], sourcePointer = '') => {
    const filesToMerge = pointers && pointers.length > 0 ? pointers : uniquePointer.value ? [uniquePointer.value] : []

    const requestPointers = [...new Set([...filesToMerge, sourcePointer].filter((p) => p?.trim()))]

    if (!requestPointers.length) {
      throw new Error('No valid pointer provided.')
    }

    const mergeResponse = await authFetch(API_PATHS.merge, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        pointers: requestPointers
      })
    })

    if (!mergeResponse.ok) {
      throw new Error(`Merge request failed (${mergeResponse.status})`)
    }

    const contentType = mergeResponse.headers.get('content-type') || ''

    let markdownText = ''

    if (contentType.includes('application/json')) {
      const data = await mergeResponse.json()

      markdownText = typeof data.summary === 'string' ? data.summary : JSON.stringify(data)
    } else {
      markdownText = await mergeResponse.text()
    }

    return markdownText
  }

  /* Generate PDF from markdown part */
  const generatePdfFromMarkdown = async (markdown) => {
    const pdfResponse = await authFetch(API_PATHS.mdToPDF, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ markdown: markdown })
    })

    console.log('PDF status:', pdfResponse.status)

    if (!pdfResponse.ok) {
      const errorBody = await pdfResponse.text()

      console.error('PDF ERROR:', errorBody)

      throw new Error(`PDF generation failed (${pdfResponse.status})`)
    }

    return await pdfResponse.blob()
  }

  /* Download PDF part */
  /*
  const downloadPdf = (blob, filename = 'converted.pdf') => {
    const url = window.URL.createObjectURL(blob)

    const a = document.createElement('a')

    a.href = url
    a.download = filename

    document.body.appendChild(a)

    a.click()

    a.remove()

    window.URL.revokeObjectURL(url)
  }
    */
  const downloadPdf = (blob) => {
    if (pdfUrl.value) {
      window.URL.revokeObjectURL(pdfUrl.value)
    }

    pdfUrl.value = window.URL.createObjectURL(blob)
  }

  /* Main function to complete the generation of PDF */
  const generatePDF = async (pointers = [], sourcePointer = '') => {
    try {
      isGeneratingPDF.value = true
      pdfError.value = ''

      const markdown = await mergeFiles(pointers, sourcePointer)

      mergedMarkdown.value = markdown
      mergedHtmlRaw.value = markdown

      console.log('Merged markdown:', markdown)

      const pdfBlob = await generatePdfFromMarkdown(markdown)

      downloadPdf(pdfBlob)
    } catch (error) {
      console.error(error)

      pdfError.value = error.message || 'An error occurred while generating PDF.'
    } finally {
      isGeneratingPDF.value = false
    }
  }
  return { generatePDF, mergedMarkdown, mergedHtml, pdfError, isGeneratingPDF, pdfUrl }
}
