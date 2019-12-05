import React from 'react'
import PropTypes from 'prop-types'
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
      type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
    }).isRequired),
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      outputColumns: PropTypes.arrayOf(PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'datetime']).isRequired
      }).isRequired) // null while rendering
    }).isRequired).isRequired,
    selectedTab: PropTypes.string // slug, may be null
  }

  handleChangeOn = (colnames) => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      on: colnames
    })
  }

  handleChangeRight = (colnames) => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      right: colnames
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
        <Multicolumn
          isReadOnly={isReadOnly}
          name={`${name}[on]`}
          fieldId={`${fieldId}_on`}
          onChange={this.handleChangeOn}
          label={i18n._(t('js.params.Custom.JoinColumns.joinOn')`Join on`)}
          inputColumns={bothColumns}
          addMenuListClassName='join-on'
          noOptionsMessage={rightTab ? i18n._(/* i18n: The parameter will contain a tab name */t('js.params.Custom.JoinColumns.noColumnToJoin')`There is no column to join on in ${rightTab.name}. Columns in both tabs must have identical names and capitalization. Please edit column names.`) : undefined}
          value={value.on}
        />
        <Multicolumn
          isReadOnly={isReadOnly}
          name={`${name}[right]`}
          fieldId={`${fieldId}_right`}
          onChange={this.handleChangeRight}
          label={i18n._(t('js.params.Custom.JoinColumns.addColumns')`Add columns`)}
          inputColumns={rightColumnsNotInOn}
          value={value.right}
        />
      </>
    )
  }
}

export default withI18n()(JoinColumns)
