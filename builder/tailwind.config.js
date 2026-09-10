const path = require("path");

const appRoot = path.resolve(__dirname, "../app");

module.exports = {
  content: [
    path.join(appRoot, "templates/**/*.html"),
    path.join(appRoot, "static/js/**/*.js"),
  ],
  theme: {
    extend: {
      width: {
        "1/7": "14.285714%",
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: ["light", "dark"],
    base: true,
    styled: true,
    utils: true,
    logs: false,
    rtl: false,
    prefix: "",
    darkTheme: "dark",
  },
};
