import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { useCurriedCallback, useCurriedCallbackOrNull } from '../../utils'
import IconButton from '../../components/IconButton'
import IconMoveUp from '../../../icons/move-up.svg'
import IconMoveDown from '../../../icons/move-down.svg'
import IconDelete from '../../../icons/delete.svg'
import IconEdit from '../../../icons/edit.svg'

function BlockActions ({ onClickDelete, onClickMoveUp, onClickMoveDown, onClickEdit }) {
  return (
    <aside className='block-actions'>
      {onClickEdit ? (
        <IconButton
          name='edit'
          title={t({ id: 'js.WorkflowEditor.Report.BlockFrame.edit.hoverText', message: 'Edit' })}
          onClick={onClickEdit}
        >
          <IconEdit />
        </IconButton>
      ) : null}
      <IconButton
        name='move-up'
        disabled={onClickMoveUp === null}
        onClick={onClickMoveUp}
        title={t({ id: 'js.WorkflowEditor.Report.BlockFrame.moveUp.hoverText', message: 'Move up' })}
      >
        <IconMoveUp />
      </IconButton>
      <IconButton
        name='move-down'
        disabled={onClickMoveDown === null}
        onClick={onClickMoveDown}
        title={t({ id: 'js.WorkflowEditor.Report.BlockFrame.moveDown.hoverText', message: 'Move down' })}
      >
        <IconMoveDown />
      </IconButton>
      <IconButton
        name='delete'
        onClick={onClickDelete}
        title={t({ id: 'js.WorkflowEditor.Report.BlockFrame.delete.hoverText', message: 'Delete' })}
      >
        <IconDelete />
      </IconButton>
    </aside>
  )
}

export default function BlockFrame ({ children, isReadOnly, className, slug, onClickDelete, onClickMoveUp, onClickMoveDown, onClickEdit }) {
  const handleClickDelete = useCurriedCallback(onClickDelete, slug)
  const handleClickMoveUp = useCurriedCallbackOrNull(onClickMoveUp, slug)
  const handleClickMoveDown = useCurriedCallbackOrNull(onClickMoveDown, slug)

  return (
    <section className={`block ${className}`}>
      {isReadOnly ? null : (
        <BlockActions
          onClickDelete={handleClickDelete}
          onClickMoveUp={handleClickMoveUp}
          onClickMoveDown={handleClickMoveDown}
          onClickEdit={onClickEdit}
        />
      )}
      <div className='block-main'>{children}</div>
    </section>
  )
}
BlockFrame.defaultProps = {
  onClickEdit: null
}
BlockFrame.propTypes = {
  className: PropTypes.string.isRequired,
  isReadOnly: PropTypes.bool.isRequired,
  children: PropTypes.node.isRequired,
  slug: PropTypes.string.isRequired,
  onClickDelete: PropTypes.func.isRequired, // func(slug) => undefined
  onClickMoveDown: PropTypes.func, // or null, if this is the bottom block
  onClickMoveUp: PropTypes.func, // or null, if this is the top block
  onClickEdit: PropTypes.func // func() => undefined
}
