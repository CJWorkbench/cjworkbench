/* globals afterEach, describe, expect, it, jest */
import { mountWithI18n } from '../i18n/test-utils'
import ConnectedDataVersionModal, {
  DataVersionModal,
  formatDateUTCForTesting
} from './DataVersionModal'
import { Provider } from 'react-redux'
import configureMockStore from 'redux-mock-store'

describe('DataVersionModal', () => {
  // Make formatDate in DataVersionModal always print out UTC times
  formatDateUTCForTesting()

  const Versions = [
    { id: '2000', date: new Date(234567890), isSeen: false },
    { id: '1000', date: new Date(123456789), isSeen: true }
  ]

  let _wrapper = null

  afterEach(() => {
    if (_wrapper !== null) {
      _wrapper.unmount()
      _wrapper = null
    }
  })

  const wrapper = extraProps => {
    _wrapper = mountWithI18n(
      <DataVersionModal
        fetchStepName='fetch'
        fetchVersions={Versions}
        selectedFetchVersionId='1000'
        stepId={123}
        isAnonymous={false}
        onClose={jest.fn()}
        onChangeFetchVersionId={jest.fn()}
        onChangeNotificationsEnabled={jest.fn()}
        {...extraProps}
      />
    )
    return _wrapper
  }

  it('matches snapshot', () => {
    expect(wrapper()).toMatchSnapshot()
  })

  it('displays versions', () => {
    const w = wrapper()
    expect(w.find('label.seen.selected time').text()).toEqual(
      'Jan 2, 1970, 10:17 AM'
    )
    expect(w.find('label.unseen time').text()).toEqual('Jan 3, 1970, 5:09 PM')
  })

  it('selects a version', () => {
    const w = wrapper()

    // Click new version; verify it's clicked
    w.find('label.unseen input').simulate('change', {
      target: { checked: true }
    })
    expect(w.find('label.unseen input').prop('checked')).toBe(true)

    // Click 'Load'
    w.find('button[name="load"]').simulate('click')
    expect(w.prop('onChangeFetchVersionId')).toHaveBeenCalledWith(123, '2000')
    expect(w.prop('onClose')).toHaveBeenCalled()
  })

  it('cancels with a close button', () => {
    const w = wrapper()

    // Click new version; verify it's clicked
    w.find('label.unseen input').simulate('change', {
      target: { checked: true }
    })

    w.find('button.close').simulate('click')
    expect(w.prop('onClose')).toHaveBeenCalled()
  })

  describe('mapStateToProps', () => {
    // Assume this modal is never shown if there is no fetch module
    const IdealState = {
      modules: {
        fetch: { name: 'Fetch Stuff', loads_data: true }
      },
      steps: {
        123: {
          id: 123,
          notifications: true,
          module: 'fetch',
          versions: {
            versions: [
              ['2018-06-22T20:09:41.649Z', true],
              ['2018-06-23T20:09:41.649Z', false]
            ],
            selected: '2018-06-22T20:09:41.649Z'
          }
        }
      }
    }

    const connectedWrapper = state => {
      const store = configureMockStore([])(state)
      _wrapper = mountWithI18n(
        <Provider store={store}>
          <ConnectedDataVersionModal stepId={123} onClose={jest.fn()} />
        </Provider>
      )
      return _wrapper
    }

    // it('should set fetchModuleName', () => {
    //  const w = connectedWrapper(IdealState)
    //  // expect(w.find('p.introduction').text()).toMatch(/“Fetch Stuff”/) No introduction test for now (Pierre)
    // })

    it('should set fetchVersions', () => {
      const w = connectedWrapper(IdealState)

      expect(
        w.find('label.selected time[time="2018-06-22T20:09:41.649Z"]').length
      ).toBe(1)
      expect(
        w.find('label.unseen time[time="2018-06-23T20:09:41.649Z"]').length
      ).toBe(1)
    })
  })
})
