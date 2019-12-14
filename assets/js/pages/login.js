import bootstrap from 'bootstrap.native'

Array.prototype.forEach.call(document.querySelectorAll('div.dropdown'), (el) => {
  /* new */ bootstrap.Dropdown(el, {})
})
