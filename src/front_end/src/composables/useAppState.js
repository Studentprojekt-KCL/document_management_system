import { reactive, toRefs, watch, ref } from 'vue'
import { loadAppState, saveAppState, clearAppState } from '@/utils/state'
import { isAuthenticated } from '@/utils/authClient'
/**
 * Default structure of the app state.
 * This represents all UI states that should persist across reloads.
 */
const defaultState = () => ({
  searchMatches: [],
  searchAllMatches: [],
  selectedFile: '',
  selectedMatch: null,
  lastQuery: '',
  isPreviewOpen: false,

  aiSummary: '',
  aiSummaryHtmlRaw: '',
  summaryPointer: '',
  summaryError: '',
  isGeneratingSummary: false,

  aiRerankResults: [],
  rerankPointer: '',
  rerankError: '',
  isReranking: false
})
/** global reactive state across app */
const state = reactive(defaultState())

/* indicates when the state has been resotred from backend */
const stateReady = ref(false)

/* internal flags
 initialized = has state been intilized from backend
 restoring = prevents ssaving during restore
 saveTimeout = timer for saving
 markstatechanged_flag = tracks if state has been modified
 */
let initialized = false
let restoring = false
let saveTimeout = null
let markStateChanged_flag = false

/* marks that state has changed due to user interaction */
function markStateChanged() {
  markStateChanged_flag = true
}

/* reset local reactive state back to default */
function resetLocalState() {
  Object.assign(state, defaultState())
}

/* Restore sthate from backend
 - only runs if user is authenticated
 - merges bacend state into default structure
 - prevents triggering save during restore
 */
async function restoreStateFromBackend() {
  restoring = true
  stateReady.value = false
  try {
    const authenticated = await isAuthenticated()
    if (!authenticated) {
      resetLocalState()
      initialized = false
      return
    }

    const backendState = await loadAppState()
    console.log('loaded state: ', backendState)

    Object.assign(state, defaultState(), backendState || {})
    initialized = true
    markStateChanged_flag = false
    stateReady.value = true
  } finally {
    restoring = false
    stateReady.value = true
  }
}

/* Save function
- prevents saving too often
- only saves if state was explicitly marked as changed
- skips saving during restore or before intilization.
*/
function scheduleSave() {
  if (!initialized || restoring || !markStateChanged_flag || !stateReady.value) return

  if (saveTimeout) {
    clearTimeout(saveTimeout)
  }

  saveTimeout = setTimeout(async () => {
    await saveAppState({ ...state })
    markStateChanged_flag = false
  }, 400)
}

/* wathc the netire state deeply, triggers save when change occurs */
watch(state, scheduleSave, { deep: true })

/* clears both backend state and local reactive state, used during logout or full reset, (homebutton) as well. */
async function clearBackendAndLocalState() {
  restoring = true
  try {
    await clearAppState()
    resetLocalState()
  } finally {
    restoring = false
  }
}

/* exposes reactive stte and helper functions. */
export function useAppState() {
  return {
    ...toRefs(state),
    stateReady,
    restoreStateFromBackend,
    clearBackendAndLocalState,
    resetLocalState,
    markStateChanged
  }
}
