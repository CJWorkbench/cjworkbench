import { useCallback } from 'react'
import PropTypes from 'prop-types'
import { ComparisonOperatorPropType } from './PropTypes'
import { t } from '@lingui/macro'

export default function ComparisonOperator (props) {
  const { isReadOnly, onChange, name, value, dtype } = props
  const handleChange = useCallback(ev => {
    onChange(ev.target.value || null)
  }, [onChange])

  return (
    <select
      name={name}
      disabled={isReadOnly}
      value={value}
      onChange={handleChange}
    >
      <option value=''>
        {t({
          id: 'js.params.Condition.Comparison.selectComparison',
          comment: 'As in "select a condition relative to which we will filter". Comparison here is something of the form "IF something IS like that"',
          message: 'Select condition'
        })}
      </option>
      {dtype === 'text' ? (
        <>
          <option value='text_contains'>
            {t({
              id: 'js.params.Condition.Comparison.textContains',
              message: 'Text contains'
            })}
          </option>
          <option value='text_does_not_contain'>
            {t({
              id: 'js.params.Condition.Comparison.textDoesNotContain',
              message: 'Text does not contain'
            })}
          </option>
          <option value='text_is'>
            {t({
              id: 'js.params.Condition.Comparison.textIs',
              message: 'Text is exactly'
            })}
          </option>
          <option value='text_is_not'>
            {t({
              id: 'js.params.Condition.Comparison.textIsNot',
              message: 'Text is not exactly'
            })}
          </option>
        </>
      ) : null}
      {dtype === 'timestamp' ? (
        <>
          <option value='timestamp_is'>
            {t({
              id: 'js.params.Condition.Comparison.timestampIs',
              message: 'Timestamp is'
            })}
          </option>
          <option value='timestamp_is_not'>
            {t({
              id: 'js.params.Condition.Comparison.timestampIsNot',
              message: 'Timestamp is not'
            })}
          </option>
          <option value='timestamp_is_after'>
            {t({
              id: 'js.params.Condition.Comparison.timestampIsAfter',
              message: 'Timestamp is after'
            })}
          </option>
          <option value='timestamp_is_after_or_equals'>
            {t({
              id: 'js.params.Condition.Comparison.timestampIsAfterOrEquals',
              message: 'Timestamp is after or equals'
            })}
          </option>
          <option value='timestamp_is_before'>
            {t({
              id: 'js.params.Condition.Comparison.timestampIsBefore',
              message: 'Timestamp is before'
            })}
          </option>
          <option value='timestamp_is_before_or_equals'>
            {t({
              id: 'js.params.Condition.Comparison.timestampIsBeforeOrEquals',
              message: 'Timestamp is before or equals'
            })}
          </option>
        </>
      ) : null}
      {dtype === 'number' ? (
        <>
          <option value='number_is'>
            {t({
              id: 'js.params.Condition.Comparison.numberIs',
              message: 'Number is'
            })}
          </option>
          <option value='number_is_not'>
            {t({
              id: 'js.params.Condition.Comparison.numberIsNot',
              message: 'Number is not'
            })}
          </option>
          <option value='number_is_greater_than'>
            {t({
              id: 'js.params.Condition.Comparison.numberIsGreaterThan',
              message: 'Number is greater than'
            })}
          </option>
          <option value='number_is_greater_than_or_equals'>
            {t({
              id: 'js.params.Condition.Comparison.numberIsGreaterThanOrEqual',
              message: 'Number is greater than or equals'
            })}
          </option>
          <option value='number_is_less_than'>
            {t({
              id: 'js.params.Condition.Comparison.numberIsLessThan',
              message: 'Number is less than'
            })}
          </option>
          <option value='number_is_less_than_or_equals'>
            {t({
              id: 'js.params.Condition.Comparison.numberIsLessThanOrEqual',
              message: 'Number is less than or equals'
            })}
          </option>
        </>
      ) : null}
      <option value='cell_is_null'>
        {t({
          id: 'js.params.Condition.Comparison.cellIsNull',
          message: 'Cell is null'
        })}
      </option>
      <option value='cell_is_not_null'>
        {t({
          id: 'js.params.Condition.Comparison.cellIsNotNull',
          message: 'Cell is not null'
        })}
      </option>
      <option value='cell_is_empty'>
        {t({
          id: 'js.params.Condition.Comparison.cellIsEmpty',
          message: 'Cell is empty'
        })}
      </option>
      <option value='cell_is_not_empty'>
        {t({
          id: 'js.params.Condition.Comparison.cellIsNotEmpty',
          message: 'Cell is not empty'
        })}
      </option>
    </select>
  )
}
ComparisonOperator.propTypes = {
  isReadOnly: PropTypes.bool.isRequired,
  name: PropTypes.string.isRequired,
  value: ComparisonOperatorPropType.isRequired, // may be ''
  dtype: PropTypes.oneOf(['text', 'timestamp', 'number']).isRequired,
  onChange: PropTypes.func.isRequired // func('text_is_exactly' or other) => undefined
}
