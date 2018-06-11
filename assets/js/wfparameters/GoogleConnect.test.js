import React from 'react'
import GoogleConnect  from './GoogleConnect'
import { mount, ReactWrapper } from 'enzyme'
import { jsonResponseMock } from '../utils'
import { store,  getCurrentUserAction, disconnectCurrentUserAction } from '../workflow-reducer';
jest.mock('../workflow-reducer');

describe('GoogleConnect', () => {
  let api
  beforeEach(() => {
    api = {
      paramOauthDisconnect: jest.fn().mockImplementation(() => Promise.resolve(null)),
    }
  })

  const wrapper = (extraProps) => {
    return mount(
      <GoogleConnect
        api={api}
        paramId={321}
        secretName={'a secret'}
        {...extraProps}
        />
    )
  }

  it('matches snapshot', () => {
    const w = wrapper({})
    expect(w).toMatchSnapshot()
  })

  it('renders without a secretName', () => {
    const w = wrapper({ secretName: null })
    expect(w.find('button.connect')).toHaveLength(1)
  })

  it('disconnects', () => {
    const w = wrapper({ secretName: 'foo@example.org' })
    w.find('button.disconnect').simulate('click')
    expect(api.paramOauthDisconnect).toHaveBeenCalledWith(321)
  })
})
