import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'

export default function AllNoneButtons ({
  isReadOnly,
  onClickAll,
  onClickNone
}) {
  return (
    <div className='all-none-buttons'>
      <button
        disabled={isReadOnly}
        type='button'
        name='refine-select-all'
        title={t({
          id: 'js.params.common.AllNoneButtons.selectAll.hoverText',
          comment: "Usually meaning 'Select all values'",
          message: 'Select All'
        })}
        onClick={onClickAll}
      >
        <Trans
          id='js.params.common.AllNoneButtons.selectAll.button'
          comment="Usually meaning 'All values'"
        >
          All
        </Trans>
      </button>
      <button
        disabled={isReadOnly}
        type='button'
        name='refine-select-none'
        title={t({
          id: 'js.params.common.AllNoneButtons.selectNone.hoverText',
          comment: "Usually meaning 'Select no value'",
          message: 'Select None'
        })}
        onClick={onClickNone}
      >
        <Trans
          id='js.params.common.AllNoneButtons.selectNone.button'
          comment="Usually meaning 'No value'"
        >
          None
        </Trans>
      </button>
    </div>
  )
}
AllNoneButtons.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  onClickNone: PropTypes.func.isRequired, // func() => undefined
  onClickAll: PropTypes.func.isRequired // func() => undefined
}
