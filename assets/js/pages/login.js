import bootstrap from 'bootstrap.native'
import Popper from 'popper.js'

Array.prototype.forEach.call(document.querySelectorAll('div.dropdown'), (el) => {
  /* new */ bootstrap.Dropdown(el)
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
