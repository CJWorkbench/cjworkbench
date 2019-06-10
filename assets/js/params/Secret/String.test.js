import React from 'react'
import String_ from './String'
import { mount } from 'enzyme'

describe('Secret/String', () => {
  const wrapper = (extraProps={}) => {
    return mount(
      <String_
        isReadOnly={false}
        name='x'
        fieldId='form123[x]'
        submitSecret={jest.fn()}
        deleteSecret={jest.fn()}
        secretLogic={{
          label: 'API key',
          placeholder: 'y',
          help: 'Basic instructions',
          helpUrl: 'http://example.org/api',
          helpUrlPrompt: 'go'
        }}
        secretMetadata={{ createdAt: '2019-06-10T15:40:12.000Z' }}
        {...extraProps}
      />
    )
  }

  describe('without a secret', () => {
    let w
    beforeEach(() => w = wrapper({ secretMetadata: null }))
    afterEach(() => { w.unmount(); w = null })

    it('renders a label', () => {
      expect(w.find('label').text()).toEqual('API key')
    })

    it('renders a text box', () => {
      expect(w.find('input[data-name="x"][type="text"]')).toHaveLength(1)
      expect(w.find('input[data-name="x"]').prop('placeholder')).toEqual('y')
    })

    it('renders help', () => {
      expect(w.find('p.help .text').text()).toEqual('Basic instructions')
      expect(w.find('p.help a').text()).toEqual('go')
      expect(w.find('p.help a').prop('target')).toEqual('_blank')
      expect(w.find('p.help a').prop('href')).toEqual('http://example.org/api')
    })

    it('submits, disabling input and button immediately', () => {
      w.find('input[data-name="x"]').simulate('change', { target: { value: 'abc123' } })
      w.find('button.set-secret').simulate('click')
      const submitSecret = w.prop('submitSecret')
      expect(submitSecret).toHaveBeenCalled()
      expect(submitSecret.mock.calls[0][0]).toEqual('x')
      expect(submitSecret.mock.calls[0][1].secret).toEqual('abc123')
      expect(submitSecret.mock.calls[0][1].createdAt).toMatch(/^\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d\.\d\d\dZ$/)

      expect(w.find('input[data-name="x"]').prop('disabled')).toBe(true)
      expect(w.find('button.set-secret').prop('disabled')).toBe(true)
    })
  })

  describe('with a secret', () => {
    let w
    beforeEach(() => w = wrapper({ secretMetadata: { createdAt: '2019-06-10T15:40:12.000Z' }}))
    afterEach(() => { w.unmount(); w = null })

    it('renders the label', () => {
      expect(w.find('label').text()).toEqual('API key')
    })

    it('renders a timestamp', () => {
      expect(w.find('time')).toHaveLength(1)
      expect(w.find('time').prop('dateTime')).toEqual('2019-06-10T15:40:12.000Z')
      expect(w.find('time').text()).toMatch(/ ago/)
    })

    it('deletes, disabling the delete button immediately', () => {
      w.find('button.clear-secret').simulate('click')
      expect(w.prop('deleteSecret')).toHaveBeenCalledWith('x')
      expect(w.find('button.clear-secret').prop('disabled')).toBe(true)
    })

    it('does not render help', () => {
      expect(w.find('p.help')).toHaveLength(0)
    })
  })
})
