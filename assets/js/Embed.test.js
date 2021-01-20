/* globals beforeEach, describe, expect, it */
import React from 'react'
import Embed from './Embed'
import { mountWithI18n } from './i18n/test-utils'

describe('Embed', () => {
  let wrapper

  describe('Available workflow', () => {
    beforeEach(() => {
      wrapper = mountWithI18n(
        <Embed
          step={{
            id: 1
          }}
          workflow={{
            name: 'Workflow Title',
            owner_name: 'Workflow Owner Name',
            last_update: '2021-01-20T15:03:12.12213Z',
            id: 1
          }}
        />
      )
    })

    it('Renders the embed widget with the correct information', () => {
      expect(wrapper).toMatchSnapshot()
      expect(wrapper.find('h1').text()).toBe('Workflow Title')
    })

    it('Displays the sharing overlay', () => {
      wrapper.find('button[name="embed"]').simulate('click')
      expect(wrapper.find('.embed-overlay').hasClass('open')).toBe(true)
    })
  })

  describe('Unavailable workflow', () => {
    beforeEach(() => {
      wrapper = mountWithI18n(
        <Embed
          step={null}
          workflow={null}
        />
      )
    })

    it('Renders the embed widget with the correct information', () => {
      expect(wrapper).toMatchSnapshot()
      expect(wrapper.find('.not-available').length).toBe(1)
    })
  })
})
