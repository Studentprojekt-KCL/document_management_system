/* ClassificationEditor Tests */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import ClassificationEditor from '@/components/ClassificationEditor.vue'

/* Mock useFilters before importing the component */
const mockSecurityLevels = ['Public', 'Internal', 'Sensitive', 'Confidential']

vi.mock('@/composables/useFilters', () => ({
  useSecurityFilters: () => mockSecurityLevels
}))

describe('ClassificationEditor', () => {
  const defaultProps = {
    visible: true,
    currentLevel: 'Public'
  }

  const mountEditor = (props = {}) => {
    return mount(ClassificationEditor, {
      props: { ...defaultProps, ...props },
      global: {
        stubs: {
          Transition: false
        }
      }
    })
  }

  /* ── Rendering ── */
  describe('rendering', () => {
    it('renders the modal when visible is true', () => {
      const wrapper = mountEditor()
      expect(wrapper.find('.classification-modal').exists()).toBe(true)
    })

    it('does not render the modal when visible is false', () => {
      const wrapper = mountEditor({ visible: false })
      expect(wrapper.find('.classification-modal').exists()).toBe(false)
    })

    it('renders all security levels as options', () => {
      const wrapper = mountEditor()
      const options = wrapper.findAll('.level-option')
      expect(options).toHaveLength(4)
      expect(options[0].text()).toBe('Public')
      expect(options[1].text()).toBe('Internal')
      expect(options[2].text()).toBe('Sensitive')
      expect(options[3].text()).toBe('Confidential')
    })

    it('shows the modal title', () => {
      const wrapper = mountEditor()
      expect(wrapper.find('.modal-title').text()).toContain('Edit Security Classification')
    })

    it('shows the description text', () => {
      const wrapper = mountEditor()
      expect(wrapper.find('.modal-description').text()).toContain('Select the appropriate security level')
    })
  })

  /* ── Level selection ── */
  describe('level selection', () => {
    it('pre-selects the current level when modal opens', async () => {
      const wrapper = mountEditor({ visible: false, currentLevel: 'Sensitive' })
      await wrapper.setProps({ visible: true }) // Simulate opening the modal
      await nextTick()

      const selected = wrapper.find('.level-option.selected')
      expect(selected.exists()).toBe(true)
      expect(selected.text()).toBe('Sensitive')
    })

    it('selects a level when clicked', async () => {
      const wrapper = mountEditor({ currentLevel: '' })
      await nextTick()

      const options = wrapper.findAll('.level-option')
      await options[2].trigger('click') // Sensitive

      expect(options[2].classes()).toContain('selected')
    })

    it('deselects the previous level when a new one is clicked', async () => {
      const wrapper = mountEditor({ currentLevel: 'Public' })
      await nextTick()

      const options = wrapper.findAll('.level-option')
      await options[3].trigger('click') // Confidential

      expect(options[0].classes()).not.toContain('selected')
      expect(options[3].classes()).toContain('selected')
    })

    it('applies the correct color class for each level', async () => {
      const wrapper = mountEditor({ currentLevel: '' })
      await nextTick()

      const options = wrapper.findAll('.level-option')
      expect(options[0].classes()).toContain('option-public')
      expect(options[1].classes()).toContain('option-internal')
      expect(options[2].classes()).toContain('option-sensitive')
      expect(options[3].classes()).toContain('option-confidential')
    })
  })

  /* ── Save ── */
  describe('save', () => {
    it('emits save with the selected level when Save is clicked', async () => {
      const wrapper = mountEditor({ visible: false, currentLevel: 'Internal' })
      await wrapper.setProps({ visible: true }) // Simulate opening the modal
      await nextTick()

      await wrapper.find('.save-btn').trigger('click')

      expect(wrapper.emitted('save')).toBeTruthy()
      expect(wrapper.emitted('save')[0]).toEqual(['Internal'])
    })

    it('does not emit save when no level is selected', async () => {
      const wrapper = mountEditor({ currentLevel: '' })
      await nextTick()

      await wrapper.find('.save-btn').trigger('click')

      expect(wrapper.emitted('save')).toBeFalsy()
    })

    it('disables the save button when no level is selected', async () => {
      const wrapper = mountEditor({ currentLevel: '' })
      await nextTick()

      const saveBtn = wrapper.find('.save-btn')
      expect(saveBtn.attributes('disabled')).toBeDefined()
    })

    it('enables the save button when a level is selected', async () => {
      const wrapper = mountEditor({ visible: false, currentLevel: 'Public' })
      await wrapper.setProps({ visible: true }) // Simulate opening the modal
      await nextTick()

      const saveBtn = wrapper.find('.save-btn')
      expect(saveBtn.attributes('disabled')).toBeUndefined()
    })

    it('shows Saving text after clicking save', async () => {
      const wrapper = mountEditor({ visible: false, currentLevel: 'Public' })
      await wrapper.setProps({ visible: true })
      await nextTick()

      await wrapper.find('.save-btn').trigger('click')
      await nextTick()

      expect(wrapper.find('.save-btn').text()).toContain('Saving')
    })
  })

  /* ── Cancel ── */
  describe('cancel', () => {
    it('emits cancel when Cancel button is clicked', async () => {
      const wrapper = mountEditor()

      await wrapper.find('.cancel-btn').trigger('click')

      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('emits cancel when backdrop is clicked', async () => {
      const wrapper = mountEditor()

      await wrapper.find('.classification-modal-backdrop').trigger('click')

      expect(wrapper.emitted('cancel')).toBeTruthy()
    })

    it('does not emit cancel when modal body is clicked', async () => {
      const wrapper = mountEditor()

      await wrapper.find('.classification-modal').trigger('click')

      expect(wrapper.emitted('cancel')).toBeFalsy()
    })
  })

  /* ── resetSaving (exposed method) ── */
  describe('resetSaving', () => {
    it('resets the saving state via exposed method', async () => {
      const wrapper = mountEditor({ visible: false, currentLevel: 'Public' })
      await wrapper.setProps({ visible: true })
      await nextTick()

      // Trigger save to set isSaving
      await wrapper.find('.save-btn').trigger('click')
      await nextTick()
      expect(wrapper.find('.save-btn').text()).toContain('Saving')

      // Call exposed resetSaving
      wrapper.vm.resetSaving()
      await nextTick()
      expect(wrapper.find('.save-btn').text()).toContain('Save')
    })
  })

  /* ── Re-opening behavior ── */
  describe('re-opening', () => {
    it('syncs to new currentLevel when modal re-opens', async () => {
      const wrapper = mountEditor({ visible: false, currentLevel: 'Public' })

      // Open with a different level
      await wrapper.setProps({ visible: true, currentLevel: 'Confidential' })
      await nextTick()

      const selected = wrapper.find('.level-option.selected')
      expect(selected.text()).toBe('Confidential')
    })
  })
})
