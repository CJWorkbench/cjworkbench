/* globals describe, expect, it, jest */
import ExportModal from './ExportModal'
import { mountWithI18n } from './i18n/test-utils'

describe('ExportModal', () => {
  const wrapper = () =>
    mountWithI18n(<ExportModal stepId={415} open toggle={jest.fn()} />)

  it('should match snapshot', () => {
    const w = wrapper()
    expect(w).toMatchSnapshot()
  })

  it('closes', () => {
    const w = wrapper()
    w.find('button.test-done-button').simulate('click')
    expect(w.prop('toggle')).toHaveBeenCalled()
  })

  it('should render download links', () => {
    const w = wrapper()
    expect(
      w.find('input[value="http://localhost/public/moduledata/live/415.csv"]')
        .length
    ).toEqual(1)
    expect(
      w.find('input[value="http://localhost/public/moduledata/live/415.json"]')
        .length
    ).toEqual(1)
  })

  it('Renders modal links which can be downloaded', () => {
    const w = wrapper()
    expect(
      w.find('a[href="http://localhost/public/moduledata/live/415.csv"]').text()
    ).toEqual('Download')
    expect(
      w
        .find('a[href="http://localhost/public/moduledata/live/415.json"]')
        .text()
    ).toEqual('Download')
  })
})
