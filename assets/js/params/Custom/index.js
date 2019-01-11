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
import Refine from './Refine'
import RenameEntries from './RenameEntries'
import ReorderHistory from './ReorderHistory'
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
  refine: Refine,
  'rename-entries': RenameEntries,
  'reorder-history': ReorderHistory,
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
