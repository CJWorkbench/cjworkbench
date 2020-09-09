import Dropdown from 'bootstrap.native/dist/components/dropdown-native.esm.js'
import Popper from 'popper.js'

Array.prototype.forEach.call(document.querySelectorAll('div.dropdown'), (el) => {
  const dropdown = new Dropdown(el) // eslint-disable-line no-unused-vars
  let popper = null

  el.parentNode.addEventListener('shown.bs.dropdown', (ev) => {
    const toggleEl = el.querySelector('.dropdown-toggle')
    const menuEl = el.querySelector('.dropdown-menu')

    popper = new Popper(toggleEl, menuEl)
  })

  el.parentNode.addEventListener('hidden.bs.dropdown', () => {
    popper.destroy()
    popper = null
  })
})
