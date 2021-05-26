import { NullCell, TextCell, TimestampCell, getDateCellComponent, makeNumberCellComponent } from '../BigTable/Cell'

const TypeToCellFormatter = {
  date: ({ unit }) => getDateCellComponent(unit),
  number: ({ format }) => makeNumberCellComponent(format),
  text: () => TextCell,
  timestamp: () => TimestampCell
}

export function columnToCellFormatter (column) {
  return TypeToCellFormatter[column.type](column) || NullCell
}
