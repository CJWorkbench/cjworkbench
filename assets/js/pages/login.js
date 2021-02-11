import Dropdown from 'bootstrap.native/dist/components/dropdown-native.esm.js'
import { createPopper } from '@popperjs/core'

Array.prototype.forEach.call(document.querySelectorAll('div.dropdown'), el => {
  const dropdown = new Dropdown(el) // eslint-disable-line no-unused-vars
  let popper = null

  el.parentNode.addEventListener('shown.bs.dropdown', ev => {
    const toggleEl = el.querySelector('.dropdown-toggle')
    const menuEl = el.querySelector('.dropdown-menu')

    popper = createPopper(toggleEl, menuEl)
  })

  el.parentNode.addEventListener('hidden.bs.dropdown', () => {
    popper.destroy()
    popper = null
  })
})
