import React from 'react'
import PropTypes from 'prop-types'
import Checkbox from '../Checkbox'
import Multicolumn from '../Multicolumn'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class JoinColumns extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func({ on: '...', right: '...' }) => undefined
    fieldId: PropTypes.string.isRequired, // <input id=...>
    name: PropTypes.string.isRequired, // <input name=...>
    label: PropTypes.string.isRequired,
    value: PropTypes.shape({
      on: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // column list
      right: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired // column list
    }).isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf(['text', 'number', 'timestamp']).isRequired
    }).isRequired),
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      outputColumns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'timestamp']).isRequired
      }).isRequired) // null while rendering
    }).isRequired).isRequired,
    selectedTab: PropTypes.string // slug, may be null
  }

  handleChangeOn = (on) => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      on
    })
  }

  handleChangeRight = (right) => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      right
    })
  }

  handleChangeRightAll = (rightAll) => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      rightAll
    })
  }

  render () {
    const { isReadOnly, name, value, inputColumns, fieldId, tabs, selectedTab, i18n } = this.props
    const rightTab = tabs.find(({ slug }) => selectedTab === slug)

    const inputColnames = (inputColumns || []).map(({ name }) => name)

    // Empty/rendering tab? Empty options
    const rightColumns = (rightTab && rightTab.outputColumns) || []
    const bothColumns = rightColumns.filter(({ name }) => inputColnames.includes(name))
    const rightColumnsNotInOn = rightColumns.filter(({ name }) => !value.on.includes(name))

    return (
      <>
        <div className='param param-multicolumn'>
          <Multicolumn
            isReadOnly={isReadOnly}
            name={`${name}[on]`}
            fieldId={`${fieldId}_on`}
            onChange={this.handleChangeOn}
            label={i18n._(/* i18n: This refers to a join operation, as the term join is used in SQL database language. It is followed by one or more column names. */t('js.params.Custom.JoinColumns.joinOn')`Join on`)}
            inputColumns={bothColumns}
            addMenuListClassName='join-on'
            noOptionsMessage={rightTab ? i18n._(/* i18n: The parameter will contain a tab name */t('js.params.Custom.JoinColumns.noColumnToJoin')`There is no column to join on in ${rightTab.name}. Columns in both tabs must have identical names and capitalization. Please edit column names.`) : undefined}
            value={value.on}
          />
        </div>
        {value.rightAll ? null : (
          <div className='param param-multicolumn'>
            <Multicolumn
              isReadOnly={isReadOnly}
              name={`${name}[right]`}
              fieldId={`${fieldId}_right`}
              onChange={this.handleChangeRight}
              label={i18n._(t('js.params.Custom.JoinColumns.addColumns')`Add columns`)}
              inputColumns={rightColumnsNotInOn}
              value={value.right}
            />
          </div>
        )}
        <div className='param param-checkbox'>
          <Checkbox
            isReadOnly={isReadOnly}
            name={`${name}[rightAll]`}
            fieldId={`${fieldId}_rightAll`}
            onChange={this.handleChangeRightAll}
            label={i18n._(t('js.params.Custom.JoinColumns.addAllColumns')`Add all columns`)}
            value={value.rightAll}
          />
        </div>
      </>
    )
  }
}

export default withI18n()(JoinColumns)
