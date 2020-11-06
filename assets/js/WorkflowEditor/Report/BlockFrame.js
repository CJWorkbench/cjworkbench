import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'
import { useCurriedCallback, useCurriedCallbackOrNull } from '../../utils'

function BlockActions ({ onClickDelete, onClickMoveUp, onClickMoveDown, onClickEdit, i18n }) {
  return (
    <aside className='block-actions'>
      <button
        className='btn context-button'
        name='delete'
        onClick={onClickDelete}
        title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.delete.hoverText')`Delete`)}
      >
        <i className='icon icon-bin' />
      </button>
      {onClickEdit ? (
        <button
          className='btn context-button'
          name='edit'
          onClick={onClickEdit}
          title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.edit.hoverText')`Edit`)}
        >
          <i className='icon icon-note' />
        </button>
      ) : null}
      <button
        className='btn context-button'
        name='move-up'
        disabled={onClickMoveUp === null}
        onClick={onClickMoveUp}
        title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.moveUp.hoverText')`Move up`)}
      >
        <i className='icon icon-caret-up' />
      </button>
      <button
        className='btn context-button'
        name='move-down'
        disabled={onClickMoveDown === null}
        onClick={onClickMoveDown}
        title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.moveDown.hoverText')`Move down`)}
      >
        <i className='icon icon-caret-down' />
      </button>
    </aside>
  )
}

function BlockFrame ({ children, className, slug, onClickDelete, onClickMoveUp, onClickMoveDown, onClickEdit, i18n }) {
  const handleClickDelete = useCurriedCallback(onClickDelete, slug)
  const handleClickMoveUp = useCurriedCallbackOrNull(onClickMoveUp, slug)
  const handleClickMoveDown = useCurriedCallbackOrNull(onClickMoveDown, slug)

  return (
    <section className={`block ${className}`}>
      <div className='block-main'>{children}</div>
      <BlockActions
        i18n={i18n}
        onClickDelete={handleClickDelete}
        onClickMoveUp={handleClickMoveUp}
        onClickMoveDown={handleClickMoveDown}
        onClickEdit={onClickEdit}
      />
    </section>
  )
}
BlockFrame.defaultProps = {
  onClickEdit: null
}
BlockFrame.propTypes = {
  className: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  slug: PropTypes.string.isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func, // or null, if this is the top block
  onClickEdit: PropTypes.func // func() => undefined
}

export default withI18n()(BlockFrame)
