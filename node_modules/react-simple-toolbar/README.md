# react-simple-toolbar

> A carefully crafted toolbar for React

No support for overflowing items

## Install

```sh
$ npm install react-simple-toolbar --save
```

## Usage

```jsx
var Toolbar = require('react-simple-toolbar')
var Region  = Toolbar.Region

<Toolbar>
    <Region>
        Export
    </Region>

    <Region flex={2}>
        <Toolbar>
            <Region align="center">Import from CSV</Region>
            <Region align="center">Import from Excel</Region>
        </Toolbar>
    </Region>

    <Region>
        Save
    </Region>
</Toolbar>

//second example
<Toolbar>
    <Region align="left">
        Export
    </Region>

    <Region align="right">
        Save
    </Region>
</Toolbar>
```

## Props (for Toolbar.Region)

 * align: String - either 'left', 'right' or 'center'

 If you don't specify an align, here is how it will behave:
  * if you only have 1 region in the toolbar, it will align 'left'
  * if you have 2 regions in the toolbar, the first will align 'left', the second will align 'right'
  * if you have 3 regions, they will align 'left', 'center' and 'right'

 If you have no region in the toolbar, one will be created by default and will contain all toolbar children.

 * flex: Number/String

 ## Changelog

 See [changelog](./CHANGELOG.md)

 ## Contributing

 Use [Github issues](https://github.com/zippyui/react-simple-toolbar/issues) for feature requests and bug reports.

 We actively welcome pull requests.

 For setting up the project locally, use:

 ```sh
 $ git clone https://github.com/zippyui/react-simple-toolbar
 $ cd react-simple-toolbar
 $ npm install
 $ npm serve # to start http server
 $ npm dev   * to start webpack-dev-server
 ```

 Now navigate to [localhost:9091](http://localhost:9091/)

 Before building a new version, make sure you run

 ```sh
 $ npm run build
 ```
 which compiles the `src` folder (which contains jsx files) into the `lib` folder (only valid EcmaScript 5 files).

 ## License

 #### MIT