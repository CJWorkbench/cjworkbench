import PopperJs from 'popper.js'

export default class Popper {
  constructor () {
    return {
      destroy: () => {},
      scheduleUpdate: () => {}
    }
  }
}

Popper.placements = PopperJs.placements
