import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export function AllNoneButtons ({ isReadOnly, onClickAll, onClickNone, i18n }) {
  return (
    <div className='all-none-buttons'>
      <button
        disabled={isReadOnly}
        type='button'
        name='refine-select-all'
        title={i18n._(t('js.params.AllNoneButtons.selectAll.title')`Select All`)}
        onClick={onClickAll}
      >
        <Trans id='js.params.AllNoneButtons.All'>All</Trans>
      </button>
      <button
        disabled={isReadOnly}
        type='button'
        name='refine-select-none'
        title={i18n._(t('js.params.AllNoneButtons.selectNone.title')`Select None`)}
        onClick={onClickNone}
      >
        <Trans id='js.params.AllNoneButtons.None'>None</Trans>
      </button>
    </div>
  )
}
AllNoneButtons.propTypes =
  {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    isReadOnly: PropTypes.bool.isRequired,
    onClickNone: PropTypes.func.isRequired, // func() => undefined
    onClickAll: PropTypes.func.isRequired // func() => undefined
  }

export default withI18n()(AllNoneButtons)
