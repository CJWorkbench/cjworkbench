react-load-mask
===============

> A carefully crafted LoadMask for React

## Install

```sh
$ npm i react-load-mask --save
```

## Key features

 * adjustable size
 * adjustable visibility
 * easily themeable
 * css animations
 * small footprint

## Usage

```javascript 
import 'react-load-mask/index.css'
import LoadMask from 'react-load-mask'

<LoadMask visible={true} />
<LoadMask visible={true} size={20} />
<LoadMask visible={false} size={120} />
```

## Props

 * `visible` - defaults to `false`. Set to `true` if you want the `LoadMask` to be visible.
 * `size` - defaults to `40`. The size of the loader inside the `LoadMask`
 * `theme` - defaults to `"default"`. See the theming section below.

## Theming

The base css class of the component is `react-load-mask`.

For having the default theme, just import `react-load-mask/index.css`.
Basically, that uses `react-load-mask/base.css` (the functional styles) AND `react-load-mask/theme/default.css` (the default theme styles).

If you want to use/build another theme, you can render the `LoadMask` as:

```jsx
<LoadMask theme="custom" visible />
```

The code above makes the `LoadMask` component have the `react-load-mask--theme-custom` className.

## License

#### MIT
