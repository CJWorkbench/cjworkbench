## Synopsis

Displays a column chart based on your data in Workbench

## Installation

Click "Add custom module" in Workbench and paste the Github URL. Voila!

## Development

The best way is to install the module and then clone the repository on your local machine.

Then,

```
cd path/to/workbench/importedmodules/columnchart/<version>
rm columnchart.html
ln -s path/to/columnchart/repo/columnchart.html ./
```

Now any changes made on your local copy of columnchart will appear immediately in Workbench.

## Build
Before building, run:
```
npm install
```

For development:
```
npm run-script build:watch
```

For production (before committing):
```
npm run-script build:production
```
