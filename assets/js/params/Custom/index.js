import Aggregations from './Aggregations'
import CellEdits from './CellEdits'
import ChartSeriesMultiSelect from './ChartSeriesMultiSelect'
import Groups from './Groups'
import JoinColumns from './JoinColumns'
import Refine from './Refine'
import Renames from './Renames'
import ReorderHistory from './ReorderHistory'
import SortColumns from './SortColumn'
import ValueSelect from './ValueSelect'
import VersionSelect from './VersionSelect'
import { Trans } from '@lingui/macro'

const Components = {
  aggregations: Aggregations,
  celledits: CellEdits,
  groups: Groups,
  join_columns: JoinColumns,
  refine: Refine,
  renames: Renames,
  'reorder-history': ReorderHistory,
  sort_columns: SortColumns,
  valueselect: ValueSelect,
  version_select: VersionSelect,
  y_columns: ChartSeriesMultiSelect
}

const ComponentNotFound = ({ name }) => (
  <p className='error'>
    <Trans
      id='js.params.Custom.ComponentNotFound.error'
      comment='The parameter will the the name of the custom type'
    >
      Custom type {name} not handled
    </Trans>
  </p>
)

export default function Custom (props) {
  const Component = Components[props.name] || ComponentNotFound
  return <Component {...props} />
}
