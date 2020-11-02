/* globals expect, test */
import React from 'react'
import { render } from '@testing-library/react'

import TileGap from './TileGap'

test('renders a gap', () => {
  const { container } = render(
    <table>
      <TileGap
        nRows={120}
        nColumns={5}
      />
    </table>
  )
  expect(container.querySelector('td')).toHaveAttribute('rowSpan', '120')
  expect(container.querySelector('td')).toHaveAttribute('colSpan', '6') // includes one for row-number
})
