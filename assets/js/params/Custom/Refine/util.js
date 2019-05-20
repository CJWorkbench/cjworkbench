export const ValueCollator = new Intl.Collator() // in the user's locale

/**
 * A collection of values the user can see and manipulate.
 *
 * It has the following properties:
 *
 * * `name`: (string) the value the Refine module will output
 * * `values`: (Array[string]) input values to rename (length >= 1)
 * * `count`: number of records with a value in `values`
 */
export class Group {
  constructor (name, values, count) {
    this.name = name
    this.values = values
    this.count = count
  }

  get isEdited () {
    if (!this.values) return undefined // React dev tools
    return this.values.length > 1 || this.values[0] !== this.name
  }
}

/**
 * Return `Group`s: outputs, and their input
 */
export function buildGroupsForValueCounts (valueCounts, renames) {
  if (!valueCounts) return []

  const groups = []
  const groupsByName = {}
  for (const value in valueCounts) {
    const count = valueCounts[value]
    const groupName = value in renames ? renames[value] : value

    if (groupName in groupsByName) {
      const group = groupsByName[groupName]
      group.values.push(value)
      group.count += count
    } else {
      const group = new Group(groupName, [ value ], count)
      groups.push(group)
      groupsByName[groupName] = group
    }
  }

  // Sort groups alphabetically
  groups.sort((a, b) => ValueCollator.compare(a.name, b.name))

  return groups
}

export function rename (renames, fromGroup, toGroup) {
  return massRename(renames, { [fromGroup]: toGroup })
}

export function massRename (renames, groupMap) {
  const newRenames = Object.assign({}, renames)

  // Rewrite every value=>fromGroup to be value=>toGroup
  for (const oldValue in renames) {
    const oldGroup = renames[oldValue]
    if (oldGroup in groupMap) {
      const toGroup = groupMap[oldGroup]
      newRenames[oldValue] = toGroup
    }
  }

  // Now do the simple rewrite of fromGroup=>toGroup
  for (const fromGroup in groupMap) {
    if (!(fromGroup in newRenames)) {
      const toGroup = groupMap[fromGroup]
      newRenames[fromGroup] = toGroup
    }
  }

  // And delete duplicates
  for (const fromGroup in groupMap) {
    if (newRenames[fromGroup] === fromGroup) {
      delete newRenames[fromGroup]
    }
  }

  return newRenames
}

export function resetGroup (renames, group) {
  const newRenames = { ...renames }

  for (const key in renames) {
    if (renames[key] === group) {
      delete newRenames[key]
    }
  }

  return newRenames
}

export function resetValue (renames, value) {
  const newRenames = { ...renames }
  delete newRenames[value]
  return newRenames
}
