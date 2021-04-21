import { NullCell, TextCell, TimestampCell, makeDateCellComponent, makeNumberCellComponent } from '../BigTable/Cell'

const TypeToCellFormatter = {
  date: ({ unit }) => makeDateCellComponent(unit),
  number: ({ format }) => makeNumberCellComponent(format),
  text: () => TextCell,
  timestamp: () => TimestampCell
}

export function columnToCellFormatter (column) {
  return TypeToCellFormatter[column.type](column) || NullCell
}
