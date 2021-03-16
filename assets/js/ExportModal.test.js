/* globals describe, expect, it, jest */
import ExportModal from './ExportModal'
import { mountWithI18n } from './i18n/test-utils'

describe('ExportModal', () => {
  const wrapper = () =>
    mountWithI18n(<ExportModal workflowId={123} stepSlug='step-1' open toggle={jest.fn()} />)

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
      w.find('input[value="http://localhost/workflows/123/steps/step-1/current-result-table.csv"]')
        .length
    ).toEqual(1)
    expect(
      w.find('input[value="http://localhost/workflows/123/steps/step-1/current-result-table.json"]')
        .length
    ).toEqual(1)
    expect(
      w.find('a[href="http://localhost/workflows/123/steps/step-1/current-result-table.csv"]').text()
    ).toEqual('Download')
    expect(
      w.find('a[href="http://localhost/workflows/123/steps/step-1/current-result-table.json"]').text()
    ).toEqual('Download')
  })
})
