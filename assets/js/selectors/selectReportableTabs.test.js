/* globals expect, test */
import selectReportableTabs from './selectReportableTabs'

test('select emptiness', () => {
  expect(
    selectReportableTabs({
      workflow: {
        tab_slugs: ['tab-1']
      },
      tabs: {
        'tab-1': { name: 'Tab 1', step_ids: [] }
      },
      steps: {},
      modules: {}
    })
  ).toEqual([{ slug: 'tab-1', name: 'Tab 1', chartSteps: [] }])
})

test('select chart steps, in order', () => {
  expect(
    selectReportableTabs({
      workflow: {
        tab_slugs: ['tab-1']
      },
      tabs: {
        'tab-1': { name: 'Tab 1', step_ids: [3, 2, 1, 4] }
      },
      steps: {
        3: { slug: 'step-3', module: 'chart1' },
        2: { slug: 'step-2', module: 'chart2' },
        1: { slug: 'step-1', module: 'nochart' },
        4: { slug: 'step-1', module: null }
      },
      modules: {
        chart1: { name: 'Charty1', has_html_output: true },
        chart2: { name: 'Charty2', has_html_output: true },
        nochart: { name: 'No-chart', has_html_output: false }
      }
    })
  ).toEqual([
    {
      slug: 'tab-1',
      name: 'Tab 1',
      chartSteps: [
        { slug: 'step-3', moduleName: 'Charty1' },
        { slug: 'step-2', moduleName: 'Charty2' }
      ]
    }
  ])
})

test('select tabs in order', () => {
  expect(
    selectReportableTabs({
      workflow: {
        tab_slugs: ['tab-2', 'tab-1']
      },
      tabs: {
        'tab-1': { name: 'Tab 1', step_ids: [] },
        'tab-2': { name: 'Tab 2', step_ids: [] }
      },
      steps: {},
      modules: {}
    })
  ).toEqual([
    { slug: 'tab-2', name: 'Tab 2', chartSteps: [] },
    { slug: 'tab-1', name: 'Tab 1', chartSteps: [] }
  ])
})
