import { useSearchMetadata } from '@/composables/useSearchMetadata'
import { authFetch, API_PATHS } from '@/utils/api'
import { useReload } from '@/composables/useReload'

export function useMdToPdf(props = {}) {
  /* Unique pointer from metadata */
  const { uniquePointer } = useSearchMetadata(props)

  /* PDF generation state */
  const { state: pdfPointer } = useReload('pdfPointer', '')
  const { state: pdfError } = useReload('pdfError', '')
  const { state: isGeneratingPDF } = useReload('isGeneratingPDF', false)

  /* Backend currently supports one pointer only. */
  const generatePDF = async (sourcePointer = '') => {
    if (!uniquePointer.value && !sourcePointer) {
      pdfError.value = 'No valid pointer provided for PDF generation.'
      return
    }

    isGeneratingPDF.value = true
    pdfError.value = ''
    pdfPointer.value = ''

    try {
      const pointer = String(sourcePointer || uniquePointer.value || '').trim()
      console.log('[mdToPdf] sending pointer:', pointer)
      const response = await authFetch(API_PATHS.mdToPDF, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pointers: [pointer] })
      })

      if (!response.ok) {
        throw new Error(`PDF generation request failed (${response.status})`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = url
      a.download = 'converted.pdf'
      a.click()

      window.URL.revokeObjectURL(url)
    } catch (error) {
      pdfError.value = error.message || 'An error occurred while generating the PDF.'
    } finally {
      isGeneratingPDF.value = false
    }
  }

  return { generatePDF, pdfPointer, pdfError, isGeneratingPDF }
}
