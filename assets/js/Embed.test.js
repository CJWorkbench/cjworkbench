/* globals beforeEach, describe, expect, it */
import React from 'react'
import { Embed } from './Embed'
import { shallowWithI18n } from './i18n/test-utils'

describe('Embed', () => {
  let wrapper

  describe('Available workflow', () => {
    beforeEach(() => {
      wrapper = shallowWithI18n(
        <Embed
          wf_module={{
            id: 1
          }}
          workflow={{
            name: 'Workflow Title',
            owner_name: 'Workflow Owner Name',
            id: 1
          }}
        />
      )
    })

    it('Renders the embed widget with the correct information', () => {
      expect(wrapper).toMatchSnapshot()
      expect(wrapper.find('.embed-footer-meta .title').text()).toBe('Workflow Title')
    })

    it('Displays the sharing overlay', () => {
      wrapper.find('.embed-footer-button').simulate('click')
      expect(wrapper.find('.embed-overlay').hasClass('open')).toBe(true)
    })
  })

  describe('Unavailable workflow', () => {
    beforeEach(() => {
      wrapper = shallowWithI18n(
        <Embed
          wf_module={null}
          workflow={null}
        />
      )
    })

    it('Renders the embed widget with the correct information', () => {
      expect(wrapper).toMatchSnapshot()
      expect(wrapper.find('.embed-not-available').length).toBe(1)
    })
  })
})
