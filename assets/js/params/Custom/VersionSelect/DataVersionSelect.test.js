/* globals afterEach, describe, expect, it */
import React from 'react'
import ConnectedDataVersionSelect, { DataVersionSelect } from './DataVersionSelect'
import DataVersionModal from '../../../WorkflowEditor/DataVersionModal' // to check it's rendered in shallow()
import { mountWithI18n, shallowWithI18n } from '../../../i18n/test-utils'
import { Provider } from 'react-redux'
import configureMockStore from 'redux-mock-store'

describe('DataVersionSelect', () => {
  const wrapper = (extraProps = {}) => {
    return mountWithI18n(
      <DataVersionSelect
        wfModuleId={123}
        currentVersionIndex={0}
        nVersions={7}
        isReadOnly={false}
        {...extraProps}
      />
    )
  }

  const shallowWrapper = (extraProps = {}) => {
    return shallowWithI18n(
      <DataVersionSelect
        wfModuleId={123}
        currentVersionIndex={0}
        nVersions={7}
        isReadOnly={false}
        {...extraProps}
      />
    )
  }

  it('should match snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('should show when no data is loaded', () => {
    const w = wrapper({ nVersions: 0, currentVersionIndex: null })
    expect(w.find('.no-versions').length).toBe(1)
  })

  it('should show text when read-only', () => {
    const w = wrapper({ isReadOnly: true })
    expect(w.find('.read-only Trans[id="js.params.Custom.VersionSelect.DataVersionSelect.readOnly.label"]').prop('values')).toEqual({ 0: 7, nVersions: 7 })
  })

  it('should show a button', () => {
    const w = wrapper()
    expect(w.find('button Trans[id="js.params.Custom.VersionSelect.DataVersionSelect.versionCount"]').prop('values')).toEqual({ 0: 7, nVersions: 7 })
  })

  it('should open and close the dialog upon clicking the button', () => {
    const w = shallowWrapper()
    expect(w.find(DataVersionModal).length).toBe(0)
    w.find('button').simulate('click')
    expect(w.find(DataVersionModal).length).toBe(1)
    w.find(DataVersionModal).prop('onClose')()
    w.update()
    expect(w.find(DataVersionModal).length).toBe(0)
  })

  describe('mapStateToProps', () => {
    const IdealState = {
      workflow: {
        read_only: false,
        wf_modules: [123, 124]
      },
      wfModules: {
        123: {
          id: 123,
          versions: {
            versions: [
              ['2018-06-23T20:09:41.649Z', false],
              ['2018-06-22T20:09:41.649Z', true]
            ],
            selected: '2018-06-22T20:09:41.649Z'
          }
        },
        124: {
          id: 124
        }
      }
    }

    let _wrapper = null
    afterEach(() => {
      if (_wrapper !== null) {
        _wrapper.unmount()
        _wrapper = null
      }
    })

    const connectedWrapper = (state) => {
      const store = configureMockStore([])(state)
      _wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedDataVersionSelect wfModuleId={123} />
        </Provider>
      )
      return _wrapper
    }

    it('finds versions', () => {
      const w = connectedWrapper(IdealState)
      expect(w.find('button Trans[id="js.params.Custom.VersionSelect.DataVersionSelect.versionCount"]').prop('values')).toEqual({ 0: 1, nVersions: 2 })
    })

    it('finds isReadOnly', () => {
      const w = connectedWrapper({
        ...IdealState,
        workflow: {
          ...IdealState.workflow,
          read_only: true
        }
      })
      expect(w.find('.read-only Trans[id="js.params.Custom.VersionSelect.DataVersionSelect.readOnly.label"]').prop('values')).toEqual({ 0: 1, nVersions: 2 })
    })

    it('handles empty version list', () => {
      const w = connectedWrapper({
        ...IdealState,
        wfModules: {
          ...IdealState.wfModules,
          123: {
            ...IdealState.wfModules['123'],
            versions: { versions: [], selected: null }
          }
        }
      })
      expect(w.find('.no-versions').text()).toBe('–')
    })
  })
})
