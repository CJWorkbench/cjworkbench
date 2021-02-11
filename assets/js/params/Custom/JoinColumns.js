import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import Checkbox from '../Checkbox'
import Multicolumn from '../Multicolumn'
import { t } from '@lingui/macro'

export default class JoinColumns extends PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func({ on: '...', right: '...' }) => undefined
    fieldId: PropTypes.string.isRequired, // <input id=...>
    name: PropTypes.string.isRequired, // <input name=...>
    label: PropTypes.string.isRequired,
    value: PropTypes.shape({
      on: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // column list
      right: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired // column list
    }).isRequired,
    inputColumns: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'number', 'timestamp']).isRequired
      }).isRequired
    ),
    tabs: PropTypes.arrayOf(
      PropTypes.shape({
        slug: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired,
        outputColumns: PropTypes.arrayOf(
          PropTypes.shape({
            name: PropTypes.string.isRequired,
            type: PropTypes.oneOf(['text', 'number', 'timestamp']).isRequired
          }).isRequired
        ) // null while rendering
      }).isRequired
    ).isRequired,
    selectedTab: PropTypes.string // slug, may be null
  }

  handleChangeOn = on => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      on
    })
  }

  handleChangeRight = right => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      right
    })
  }

  handleChangeRightAll = rightAll => {
    const { onChange, value } = this.props
    onChange({
      ...value,
      rightAll
    })
  }

  render () {
    const {
      isReadOnly,
      name,
      value,
      inputColumns,
      fieldId,
      tabs,
      selectedTab
    } = this.props
    const rightTab = tabs.find(({ slug }) => selectedTab === slug)

    const inputColnames = (inputColumns || []).map(({ name }) => name)

    // Empty/rendering tab? Empty options
    const rightColumns = (rightTab && rightTab.outputColumns) || []
    const bothColumns = rightColumns.filter(({ name }) =>
      inputColnames.includes(name)
    )
    const rightColumnsNotInOn = rightColumns.filter(
      ({ name }) => !value.on.includes(name)
    )

    return (
      <>
        <div className='param param-multicolumn'>
          <Multicolumn
            isReadOnly={isReadOnly}
            name={`${name}[on]`}
            fieldId={`${fieldId}_on`}
            onChange={this.handleChangeOn}
            label={t({
              id: 'js.params.Custom.JoinColumns.joinOn',
              comment:
                'This refers to a join operation, as the term join is used in SQL database language. It is followed by one or more column names.',
              message: 'Join on'
            })}
            inputColumns={bothColumns}
            addMenuListClassName='join-on'
            noOptionsMessage={
              rightTab
                ? t({
                    comment: 'The parameter will contain a tab name',
                    id: 'js.params.Custom.JoinColumns.noColumnToJoin',
                    message:
                      'There is no column to join on in {0}. Columns in both tabs must have identical names and capitalization. Please edit column names.',
                    values: { 0: rightTab.name }
                  })
                : undefined
            }
            value={value.on}
          />
        </div>
        {value.rightAll
          ? null
          : (
            <div className='param param-multicolumn'>
              <Multicolumn
                isReadOnly={isReadOnly}
                name={`${name}[right]`}
                fieldId={`${fieldId}_right`}
                onChange={this.handleChangeRight}
                label={t({
                  id: 'js.params.Custom.JoinColumns.addColumns',
                  message: 'Add columns'
                })}
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
            label={t({
              id: 'js.params.Custom.JoinColumns.addAllColumns',
              message: 'Add all columns'
            })}
            value={value.rightAll}
          />
        </div>
      </>
    )
  }
}
