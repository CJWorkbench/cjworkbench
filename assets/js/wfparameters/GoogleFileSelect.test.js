import React from 'react'
import GoogleFileSelect  from './GoogleFileSelect'
import { mount, shallow } from 'enzyme'
import { jsonResponseMock } from '../test-utils'

const tick = async() => new Promise(resolve => setTimeout(resolve, 0))

describe('GoogleFileSelect', () => {
  const aFileMetadataJson = JSON.stringify({
    "id": "aushwyhtbndh7365YHALsdfsdf987IBHJB98uc9uisdj",
    "name": "Police Data",
  })

  // Mount is necessary to invoke componentDidMount()
  let api
  let userCreds
  let loadAccessToken
  let loadPickerFactory
  let pickerFactory
  let pickerOpen
  let pickerClose
  let fileMetadataJson
  let onChangeJson
  beforeEach(() => {
    // set default props. Tests can change them before calling wrapper()
    fileMetadataJson = aFileMetadataJson
    loadAccessToken = jest.fn().mockReturnValue(Promise.resolve({ 'access_token': 'access-token' }))
    pickerFactory = {
      open: jest.fn(),
      close: jest.fn(),
    }
    loadPickerFactory = jest.fn(() => Promise.resolve(pickerFactory))
    onChangeJson = jest.fn()
    userCreds = 0

    api = {
      currentGoogleClientAccessToken: loadAccessToken,
    }
  })

  let mountedWrapper = null
  let wrapper = () => {
    // mount(), not shallow(), because we use componentDidMount()
    return mountedWrapper = mount(
      <GoogleFileSelect
        api={api}
        userCreds={userCreds}
        fileMetadataJson={fileMetadataJson}
        onChangeJson={onChangeJson}
        loadPickerFactory={loadPickerFactory}
        />
    )
  }

  afterEach(() => {
    if (mountedWrapper) mountedWrapper.unmount()
    mountedWrapper = null
  })

  it('indicates when not connected', async () => {
    userCreds = null
    const w = wrapper()
    await tick()
    w.update()
    expect(w.find('.not-signed-in')).toHaveLength(1)
    expect(loadAccessToken).not.toHaveBeenCalled()
    expect(w.find('button')).toHaveLength(0)
  })

  it('indicates when not connected because userCreds is invalid', async () => {
    loadAccessToken.mockReturnValue(Promise.resolve(null))
    const w = wrapper()
    await tick()
    w.update()
    expect(w.find('.not-signed-in')).toHaveLength(1)
    expect(w.find('button')).toHaveLength(0)
  })

  it('shows loading when google API has not loaded', async () => {
    loadPickerFactory.mockReturnValue(new Promise(_ => {}))
    const w = wrapper()
    await tick()
    w.update()
    expect(w.find('.loading')).toHaveLength(1)
  })

  it('shows loading when access token has not loaded', async () => {
    loadAccessToken.mockReturnValue(new Promise(_ => {}))
    const w = wrapper()
    await tick()
    w.update()
    expect(w.find('.loading')).toHaveLength(1)
  })


  it('refreshes access token when changing userCreds', async () => {
    const w = wrapper()
    await tick()
    w.setProps({ userCreds: 1 })
    expect(loadAccessToken).toHaveBeenCalledTimes(2)
  })

  it('allows Change of existing file', async () => {
    fileMetadataJson = aFileMetadataJson
    const w = wrapper()
    await tick()
    w.update()
    expect(w.find('button')).toHaveLength(1)
    expect(w.find('button').text()).toEqual('Change')

    pickerFactory.open.mockImplementation((accessToken, onPick, onCancel) => {
      expect(accessToken).toEqual('access-token')
      onPick({
        id: 'newid',
        name: 'new file',
      })
    })

    w.find('button').simulate('click')
    expect(onChangeJson).toHaveBeenCalledWith(JSON.stringify({
      id: 'newid',
      name: 'new file',
    }))
  })

  it('works when pick is canceled', async () => {
    const w = wrapper()
    await tick()
    w.update()

    pickerFactory.open.mockImplementation((accessToken, onPick, onCancel) => {
      onCancel()
    })

    w.find('button').simulate('click')
    expect(onChangeJson).not.toHaveBeenCalled()
  })

  it('calls it Choose, not Change, when no file is selected', async () => {
    fileMetadataJson = null
    const w = wrapper()
    await tick()
    w.update()
    expect(w.find('button').text()).toEqual('Choose')
  })

  it('closes on unmount', async () => {
    const w = wrapper()
    await tick()
    w.update()
    w.find('button').simulate('click')
    mountedWrapper.unmount()
    mountedWrapper = null
    expect(pickerFactory.close).toHaveBeenCalled()
  })
});
