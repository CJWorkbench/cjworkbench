/* globals expect, test */
import selectReport from './selectReport'

test('select empty auto report from empty workflow', () => {
  expect(selectReport({
    workflow: {
      hasCustomReport: false,
      tab_slugs: ['tab-1']
    },
    tabs: {
      'tab-1': { step_ids: [] }
    },
    steps: {},
    modules: {}
  })).toEqual([])
})

test('select auto report with only html-output steps', () => {
  const step1 = { slug: 'step-1', module: 'chart' }
  const step4 = { slug: 'step-4', module: 'chart2' }
  expect(selectReport({
    workflow: {
      hasCustomReport: false,
      tab_slugs: ['tab-1']
    },
    tabs: {
      'tab-1': { step_ids: [1, 2, 3, 4] }
    },
    steps: {
      1: step1,
      2: { slug: 'step-2', module: 'nochart' },
      3: { slug: 'step-3', module: 'missing' },
      4: step4
    },
    modules: {
      chart: { has_html_output: true },
      nochart: { has_html_output: false },
      chart2: { has_html_output: true }
    }
  })).toEqual([
    { slug: 'block-auto-step-1', type: 'chart', step: step1 },
    { slug: 'block-auto-step-4', type: 'chart', step: step4 }
  ])
})

test('select auto report ordered across many tabs', () => {
  const step1 = { slug: 'step-1', module: 'chart' }
  const step4 = { slug: 'step-4', module: 'chart2' }
  expect(selectReport({
    workflow: {
      hasCustomReport: false,
      tab_slugs: ['tab-3', 'tab-2', 'tab-1']
    },
    tabs: {
      'tab-3': { step_ids: [1, 2] },
      'tab-2': { step_ids: [3] },
      'tab-1': { step_ids: [4] }
    },
    steps: {
      1: step1,
      2: { slug: 'step-2', module: 'nochart' },
      3: { slug: 'step-3', module: 'missing' },
      4: step4
    },
    modules: {
      chart: { has_html_output: true },
      nochart: { has_html_output: false },
      chart2: { has_html_output: true }
    }
  })).toEqual([
    { slug: 'block-auto-step-1', type: 'chart', step: step1 },
    { slug: 'block-auto-step-4', type: 'chart', step: step4 }
  ])
})

test('select empty custom report, even if auto-report would have a chart', () => {
  expect(selectReport({
    workflow: {
      hasCustomReport: true,
      tab_slugs: ['tab-1'],
      blockSlugs: []
    },
    tabs: {
      'tab-1': { step_ids: [1] }
    },
    steps: {
      1: { slug: 'step-1', module: 'chart', output_status: null, cached_render_result_delta_id: null }
    },
    modules: {
      chart: { has_html_output: true }
    }
  })).toEqual([])
})

test('select custom report with table', () => {
  expect(selectReport({
    workflow: { hasCustomReport: true, blockSlugs: ['block-1'] },
    tabs: {
      'tab-1': {
        name: 'Find me!',
        step_ids: [1, 2]
      }
    },
    steps: {
      1: { slug: 'step-1' },
      2: { slug: 'step-2', output_status: 'ok', cached_render_result_delta_id: 123 }
    },
    blocks: {
      'block-1': { type: 'table', tabSlug: 'tab-1' }
    }
  })).toEqual([
    {
      slug: 'block-1',
      type: 'table',
      tab: {
        slug: 'tab-1',
        name: 'Find me!',
        outputStep: {
          id: 2, // TODO nix IDs https://www.pivotaltracker.com/story/show/167600824
          slug: 'step-2',
          outputStatus: 'ok',
          deltaId: 123
        }
      }
    }
  ])
})

test('select custom report with table that has no steps', () => {
  expect(selectReport({
    workflow: { hasCustomReport: true, blockSlugs: ['block-1'] },
    tabs: {
      'tab-1': {
        name: 'Find me!',
        step_ids: []
      }
    },
    steps: {},
    blocks: {
      'block-1': { type: 'table', tabSlug: 'tab-1' }
    }
  })).toEqual([
    {
      slug: 'block-1',
      type: 'table',
      tab: {
        slug: 'tab-1',
        name: 'Find me!',
        outputStep: null
      }
    }
  ])
})

test('select custom report with chart', () => {
  const step1 = { slug: 'step-1', something: 'find me!' }
  expect(selectReport({
    workflow: { hasCustomReport: true, blockSlugs: ['block-1'] },
    tabs: {},
    steps: {
      1: step1
    },
    blocks: {
      'block-1': { type: 'chart', stepSlug: 'step-1' }
    }
  })).toEqual([
    { slug: 'block-1', type: 'chart', step: step1 }
  ])
})

test('select custom report with text', () => {
  expect(selectReport({
    workflow: { hasCustomReport: true, blockSlugs: ['block-1'] },
    tabs: {},
    steps: {},
    blocks: {
      'block-1': { type: 'text', markdown: 'hi!' }
    }
  })).toEqual([
    { slug: 'block-1', type: 'text', markdown: 'hi!' }
  ])
})
