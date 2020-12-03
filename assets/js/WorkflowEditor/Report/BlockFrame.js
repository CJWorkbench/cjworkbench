import React from 'react'
import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'
import { useCurriedCallback, useCurriedCallbackOrNull } from '../../utils'
import IconButton from '../../components/IconButton'
import IconMoveUp from '../../../icons/move-up.svg'
import IconMoveDown from '../../../icons/move-down.svg'
import IconDelete from '../../../icons/delete.svg'
import IconEdit from '../../../icons/edit.svg'

function BlockActions ({ onClickDelete, onClickMoveUp, onClickMoveDown, onClickEdit, i18n }) {
  return (
    <aside className='block-actions'>
      {onClickEdit ? (
        <IconButton
          name='edit'
          title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.edit.hoverText')`Edit`)}
          onClick={onClickEdit}
        >
          <IconEdit />
        </IconButton>
      ) : null}
      <IconButton
        name='move-up'
        disabled={onClickMoveUp === null}
        onClick={onClickMoveUp}
        title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.moveUp.hoverText')`Move up`)}
      >
        <IconMoveUp />
      </IconButton>
      <IconButton
        name='move-down'
        disabled={onClickMoveDown === null}
        onClick={onClickMoveDown}
        title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.moveDown.hoverText')`Move down`)}
      >
        <IconMoveDown />
      </IconButton>
      <IconButton
        name='delete'
        onClick={onClickDelete}
        title={i18n._(t('js.WorkflowEditor.Report.BlockFrame.delete.hoverText')`Delete`)}
      >
        <IconDelete />
      </IconButton>
    </aside>
  )
}

function BlockFrame ({ children, isReadOnly, className, slug, onClickDelete, onClickMoveUp, onClickMoveDown, onClickEdit, i18n }) {
  const handleClickDelete = useCurriedCallback(onClickDelete, slug)
  const handleClickMoveUp = useCurriedCallbackOrNull(onClickMoveUp, slug)
  const handleClickMoveDown = useCurriedCallbackOrNull(onClickMoveDown, slug)

  return (
    <section className={`block ${className}`}>
      {isReadOnly ? null : (
        <BlockActions
          i18n={i18n}
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

export default withI18n()(BlockFrame)
