react-menus
===========

> A carefully crafted menu for React

## Install

```sh
$ npm install react-menus --save
```

## Description

The `react-menus` component is a context-menu like widget for React. It features **smart positioning**, overflow **scrolling** on too many menu items and **smart submenu positioning**.

## Changelog

See [Changelog](./CHANGELOG.md)

## Roadmap

See [Roadmap](./ROADMAP.md)

## Usage

```jsx
var items = [
    {
        label: 'hello',
        onClick: function(itemProps, index, event) {
            console.log('well, hello')
        }
    },
    '-', //show separator
    {
        label: 'hi'
    },
    {
		label: 'export',
		disabled: true
	}
]

function onClick(event, props, index){

}

<Menu items={items} onClick={onClick}/>
```

For rendering separators, just use a `'-'` in the items array.

## Properties

 * items: Object[]
 * onClick: Function(event, props, index) - Called on a click on a direct menu item. For clicks on menu items at any level of nesting, use `onChildClick`
 * onChildClick: Function(event, props) - Called when a menu item at any level of nesting was clicked
 * columns: String[] - defaults to ['label']

For every item in the items property, a row will be rendered, with all the columns specified in `props.columns`. Every column displays the value in item[&lt;column_name&gt;].

Every item can optionally have an **onClick** property, which is called when the item is clicked. (**onClick: Function(event, itemProps, index)**). Making an item disabled is done by specifying **disabled: true** on the item object.

 * expander: String/ReactElement - an expander tool to use when a menu item has other subitems. Defaults to the unicode arrow character **›**.

### Styling & advanced usage

By default, the `react-menus` component comes with built-in structural styles as well as with styles for a default nice theme. The specified theme is applied to menu items. If you don't want to render menu items with the default theme, just specify `theme=''` (or any falsy value).

```jsx
var items = [ {label: 'Save', onClick: function(){} }, { label: 'Export'}]
<Menu theme='' items={items} />
```

Or you can specify your own theme for the button. The value for the `theme` property is just an object with different styles:

```jsx
var theme = {
	style: { background: 'blue'},
	overStyle: { background: 'red', color: 'white'},
	activeStyle: { background: 'magenta'},
	expandedStyle: { background: 'magenta'},
	disabledStyle: {background: 'gray'}
}

<Menu theme={theme} items={items} />
```

Or you can specify a theme as string: 'default'. The `'default'` theme is the only one built in.

```jsx
<Menu theme='default' />
```
But you can add named themes:
```jsx
var theme = require('react-menus').theme

theme.goldenTheme = { overStyle: {background: 'yellow'}}

<Menu theme='goldenTheme' />
```

For styling menu separators, set the desired style properties on `Menu.Separator.style`

```jsx
var Menu = require('react-menus')

var Separator = Menu.Separator

Separator.style = {
    background: 'red' //the color of the separator
}

Separator.size = 10 //will be 10 px in height
```

### Style props

Styling menu items overrides theme styles.

 * itemStyle - style to be applied to menu items. Overrides `theme.style`
 * itemOverStyle - style to be applied to menu items on mouse over. Overrides `theme.overStyle`
 * itemActiveStyle - style to be applied to menu items on mouse down on the item. Overrides `theme.activeStyle`
 * itemExpandedStyle - style to be applied to menu items when the item is expanded. Overrides `theme.expandedStyle`
 * itemDisabledStyle - style to be applied to disabled menu items. Overrides `theme.defaultStyle`

 * cellStyle - style to be applied to menu item cells (expect the expander cell).

### Scrolling

Menu scrolling is enabled by default (`enableScroll: true`). When you have too many items, and the menu is bigger than it's parent container, the menu shows a scrolling user interface.

Or you can specify a `maxHeight` property on the menu, and if that is exceeded, the menu is scrollable.

```jsx
<Menu maxHeight={200} items={items}/>
```

Of course you can turn off scrolling with `enableScroll: false`

### Smart submenus

Showing and hiding submenus is implemented with a smart algorithm, as described [here](http://bjk5.com/post/44698559168/breaking-down-amazons-mega-dropdown). Also submenu positioning is made taking into account the available space. More documentation on this soon.

## License

```MIT```