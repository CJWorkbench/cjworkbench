import React from 'react'
import PropTypes from 'prop-types'

import Aggregations from './Aggregations'
import CellEdits from './CellEdits'
import ChartSeriesMultiSelect from './ChartSeriesMultiSelect'
import Code from './Code'
import File from './File'
import Filters from './Filters'
import GoogleFileSelect from './GoogleFileSelect'
import Groups from './Groups'
import JoinColumns from './JoinColumns'
import Refine from './Refine'
import Renames from './Renames'
import ReorderHistory from './ReorderHistory'
import SortColumns from './SortColumn'
import ValueSelect from './ValueSelect'
import VersionSelect, { VersionSelectSimpler } from './VersionSelect'

const Components = {
  aggregations: Aggregations,
  celledits: CellEdits,
  code: Code,
  file: File,
  filters: Filters,
  googlefileselect: GoogleFileSelect,
  groups: Groups,
  join_columns: JoinColumns,
  refine: Refine,
  renames: Renames,
  'reorder-history': ReorderHistory,
  sort_columns: SortColumns,
  valueselect: ValueSelect,
  version_select_simpler: VersionSelectSimpler,
  version_select: VersionSelect,
  y_columns: ChartSeriesMultiSelect,
}

const ComponentNotFound = ({ name }) => (
  <p className='error'>Custom type {name} not handled</p>
)

export default function Custom (props) {
  const Component = Components[props.name] || ComponentNotFound
  return <Component {...props} />
}
