import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SearchBar from '@/components/SearchBar.vue'

describe('SearchBar', () => {
  const mountBar = (props = {}) => {
    return mount(SearchBar, {
      props: { loading: false, ...props }
    })
  }

  /* ── Rendering ── */
  describe('rendering', () => {
    it('renders the search input', () => {
      const wrapper = mountBar()
      expect(wrapper.find('.search-input').exists()).toBe(true)
    })

    it('renders the search button', () => {
      const wrapper = mountBar()
      expect(wrapper.find('.search-button').exists()).toBe(true)
      expect(wrapper.find('.search-button').text()).toBe('Search')
    })

    it('renders the search icon', () => {
      const wrapper = mountBar()
      expect(wrapper.find('.search-icon').exists()).toBe(true)
    })

    it('shows default placeholder when not loading', () => {
      const wrapper = mountBar()
      const input = wrapper.find('.search-input')
      expect(input.attributes('placeholder')).toContain('Search for documents')
    })

    it('shows loading placeholder when loading', () => {
      const wrapper = mountBar({ loading: true })
      const input = wrapper.find('.search-input')
      expect(input.attributes('placeholder')).toBe('Searching...')
    })

    it('disables input when loading', () => {
      const wrapper = mountBar({ loading: true })
      expect(wrapper.find('.search-input').attributes('disabled')).toBeDefined()
    })
  })

  /* ── Search button state ── */
  describe('search button state', () => {
    it('disables button when input is empty', () => {
      const wrapper = mountBar()
      expect(wrapper.find('.search-button').attributes('disabled')).toBeDefined()
    })

    it('disables button when input is only whitespace', async () => {
      const wrapper = mountBar()
      await wrapper.find('.search-input').setValue('   ')
      expect(wrapper.find('.search-button').attributes('disabled')).toBeDefined()
    })

    it('enables button when input has text', async () => {
      const wrapper = mountBar()
      await wrapper.find('.search-input').setValue('test query')
      expect(wrapper.find('.search-button').attributes('disabled')).toBeUndefined()
    })

    it('disables button when loading even with text', async () => {
      const wrapper = mountBar({ loading: true })
      await wrapper.find('.search-input').setValue('test query')
      expect(wrapper.find('.search-button').attributes('disabled')).toBeDefined()
    })
  })

  /* ── Search emit ── */
  describe('search emit', () => {
    it('emits search with trimmed query on form submit', async () => {
      const wrapper = mountBar()
      await wrapper.find('.search-input').setValue('  test query  ')
      await wrapper.find('form').trigger('submit')

      expect(wrapper.emitted('search')).toBeTruthy()
      expect(wrapper.emitted('search')[0]).toEqual(['test query'])
    })

    it('emits search on Enter key', async () => {
      const wrapper = mountBar()
      await wrapper.find('.search-input').setValue('hello')
      await wrapper.find('form').trigger('submit')

      expect(wrapper.emitted('search')).toBeTruthy()
      expect(wrapper.emitted('search')[0]).toEqual(['hello'])
    })

    it('does not emit search when input is empty', async () => {
      const wrapper = mountBar()
      await wrapper.find('form').trigger('submit')

      expect(wrapper.emitted('search')).toBeFalsy()
    })

    it('does not emit search when input is only whitespace', async () => {
      const wrapper = mountBar()
      await wrapper.find('.search-input').setValue('   ')
      await wrapper.find('form').trigger('submit')

      expect(wrapper.emitted('search')).toBeFalsy()
    })

    it('clears the input after successful search', async () => {
      const wrapper = mountBar()
      const input = wrapper.find('.search-input')

      await input.setValue('test query')
      await wrapper.find('form').trigger('submit')

      expect(input.element.value).toBe('')
    })
  })

  /* ── Multiple searches ── */
  describe('multiple searches', () => {
    it('can emit multiple searches in sequence', async () => {
      const wrapper = mountBar()
      const input = wrapper.find('.search-input')

      await input.setValue('first')
      await wrapper.find('form').trigger('submit')

      await input.setValue('second')
      await wrapper.find('form').trigger('submit')

      expect(wrapper.emitted('search')).toHaveLength(2)
      expect(wrapper.emitted('search')[0]).toEqual(['first'])
      expect(wrapper.emitted('search')[1]).toEqual(['second'])
    })
  })
})