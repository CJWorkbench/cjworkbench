export const errorText = {
	"EMPTY": {
		location: "input",
		text: "Enter some data above.",
		type: "error"
	},
	"UNEVEN_SERIES": {
		location: "input",
		text: "At least one row does not have the same number of columns as the rest.",
		type: "error"
	},
	"COLUMN_ZERO": {
		location: "input",
		text: "This chart that doesn't have a zero axis. Double check that this is ok.",
		type: "warning"
	},
	"TOO_MANY_SERIES": {
		location: "input",
		text: "The maximum number of columns supported to produce a chart is 12.",
		type: "error"
	},
	"TOO_FEW_SERIES": {
		location: "input",
		text: "You need at least 2 columns to produce a chart.",
		type: "error"
	},
	"NAN_VALUES": {
		location: "input",
		text: "At least one data points cannot be converted into a number.",
		type: "error"
	},
	"NOT_DATES": {
		location: "input",
		text: "A least one date in your data is the wrong format.",
		type: "error"
	},
	"TOO_MUCH_DATA": {
		location: "input",
		text: "You have more data than can be rendered or saved correctly",
		type: "warning"
	},
	"CANT_AUTO_TYPE": {
		location: "input",
		text: "The type of information in the first column of your data cannot be automatically determined.",
		type: "warning",
	},
	"UNEVEN_TICKS": {
		location: "axis",
		text: "Adjust axis settings to make your y-axis ticks even.",
		type: "warning"
	},
	"NO_PREFIX_SUFFIX": {
		location: "axis",
		text: "Prefix and suffix are missing. Consider labelling your chart.",
		type: "warning"
	},
	"LARGE_NUMBERS": {
		location: "input",
		text: "Numbers are large. Consider dividing and labelling the unit in the axis.",
		type: "warning"
	},
	"UNEVEN_TZ": {
		location: "input",
		text: "Some dates are specified with timezones and some of them are not. This may cause erroneous plotting.",
		type: "warning"
	}
};
