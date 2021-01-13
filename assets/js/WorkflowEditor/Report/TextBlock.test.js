/* globals expect, jest, test */
import React from 'react'
import { fireEvent } from '@testing-library/react'
import { renderWithI18n } from '../../i18n/test-utils'
import TextBlock from './TextBlock'

test('modify text', () => {
  const onClickDelete = jest.fn()
  const onClickMoveUp = jest.fn()
  const onClickMoveDown = jest.fn()
  const setBlockMarkdown = jest.fn()
  const { container } = renderWithI18n(
    <TextBlock
      block={{ slug: 'block-text-a', markdown: '# some text' }}
      isReadOnly={false}
      onClickDelete={onClickDelete}
      onClickMoveUp={onClickMoveUp}
      onClickMoveDown={onClickMoveDown}
      setBlockMarkdown={setBlockMarkdown}
    />
  )

  fireEvent.click(container.querySelector('[name="edit"]'))
  fireEvent.change(container.querySelector('textarea'), { target: { value: '# other text' } })
  fireEvent.click(container.querySelector('button[type="submit"]'))
  expect(setBlockMarkdown).toHaveBeenCalledWith('block-text-a', '# other text')
  expect(container.querySelector('textarea')).toBe(null)
})

test('delete the block when removing all text', () => {
  const onClickDelete = jest.fn()
  const onClickMoveUp = jest.fn()
  const onClickMoveDown = jest.fn()
  const setBlockMarkdown = jest.fn()
  const { container } = renderWithI18n(
    <TextBlock
      block={{ slug: 'block-text-a', markdown: '# some text' }}
      isReadOnly={false}
      onClickDelete={onClickDelete}
      onClickMoveUp={onClickMoveUp}
      onClickMoveDown={onClickMoveDown}
      setBlockMarkdown={setBlockMarkdown}
    />
  )

  fireEvent.click(container.querySelector('[name="edit"]'))
  fireEvent.change(container.querySelector('textarea'), { target: { value: '' } })
  fireEvent.click(container.querySelector('button[type="submit"]'))
  expect(onClickDelete).toHaveBeenCalledWith('block-text-a')
  expect(container.querySelector('textarea')).toBe(null)
})
