/* globals describe, expect, it, jest */
import React from 'react'
import Gdrivefile from './Gdrivefile'
// import { mount } from 'enzyme'
import { mountWithI18n } from '../i18n/test-utils'

const tick = async () => new Promise(resolve => setTimeout(resolve, 0))

describe('Gdrivefile', () => {
  const aFileMetadataJson = {
    id: 'aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj',
    name: 'Police Data',
    url: 'https://example.org',
    mimeType: 'text/csv'
  }

  let pickerFactory

  // Mount is necessary to invoke componentDidMount()
  const wrapper = (extraProps = {}) => {
    pickerFactory = {
      open: jest.fn(),
      close: jest.fn()
    }

    return mountWithI18n(
      <Gdrivefile
        createOauthAccessToken={jest.fn(() => Promise.resolve('access-token'))}
        isReadOnly={false}
        secretMetadata={{ name: 'user@example.org' }}
        value={aFileMetadataJson}
        onChange={jest.fn()}
        onSubmit={jest.fn()}
        loadPickerFactory={jest.fn(() => Promise.resolve(pickerFactory))}
        {...extraProps}
      />
    )
  }

  it('indicates when not connected', async () => {
    const w = wrapper({ secretMetadata: null })
    await tick()
    w.update()
    expect(w.find('.not-signed-in')).toHaveLength(1)
    expect(w.prop('createOauthAccessToken')).not.toHaveBeenCalled()
    expect(w.find('button')).toHaveLength(0)
  })

  it('shows loading when google API has not loaded', async () => {
    const w = wrapper({
      loadPickerFactory: () => new Promise(resolve => { /* never resolve */ })
    })
    await tick()
    w.update()
    expect(w.find('.loading')).toHaveLength(1)
  })

  it('shows no button or loading message when isReadOnly', async () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('button')).toHaveLength(0)
    expect(w.find('p')).toHaveLength(0)
    await tick()
    w.update()
    expect(w.find('button')).toHaveLength(0)
    expect(w.find('p')).toHaveLength(0)
  })

  it('shows loading when fetching access token', async () => {
    const w = wrapper({
      createOauthAccessToken: () => new Promise(resolve => { /* never resolve */ })
    })
    await tick()
    w.update()
    w.find('button.change-file').simulate('click')
    expect(w.find('.loading')).toHaveLength(1)
  })

  it('shows errors when unauthenticated', async () => {
    const w = wrapper({
      secretMetadata: { name: 'hi' },
      createOauthAccessToken: () => Promise.resolve(null)
    })
    await tick()
    w.update()
    w.find('button.change-file').simulate('click')
    await tick()
    w.update()
    expect(w.find('.sign-in-error')).toHaveLength(1)
  })

  it('allows Change of existing file', async () => {
    const w = wrapper({ value: aFileMetadataJson })
    await tick()
    w.update()
    expect(w.find('button')).toHaveLength(1)
    expect(w.find('button Trans[id="js.params.Gdrivefile.change.button"]')).toHaveLength(1)

    pickerFactory.open.mockImplementation((accessToken, onPick, onCancel) => {
      expect(accessToken).toEqual('access-token')
      onPick({
        id: 'newid',
        name: 'new file',
        url: 'https://example.org/2',
        mimeType: 'text/csv'
      })
    })

    w.find('button').simulate('click')
    await tick() // let fetchAccessToken() return
    expect(w.prop('onChange')).toHaveBeenCalledWith({
      id: 'newid',
      name: 'new file',
      url: 'https://example.org/2',
      mimeType: 'text/csv'
    })
    expect(w.prop('onSubmit')).toHaveBeenCalled()
  })

  it('works when pick is canceled', async () => {
    const w = wrapper()
    await tick()
    w.update()

    pickerFactory.open.mockImplementation((accessToken, onPick, onCancel) => {
      onCancel()
    })

    w.find('button').simulate('click')
    await tick() // let fetchAccessToken() return
    expect(w.prop('onChange')).not.toHaveBeenCalled()
  })

  it('calls it Choose, not Change, when no file is selected', async () => {
    const w = wrapper({ value: null })
    await tick()
    w.update()
    expect(w.find('button Trans[id="js.params.Gdrivefile.choose.button"]')).toHaveLength(1)
  })

  it('closes on unmount', async () => {
    const w = wrapper()
    await tick()
    w.update()
    w.find('button').simulate('click')
    w.unmount()
    expect(pickerFactory.close).toHaveBeenCalled()
  })
})
