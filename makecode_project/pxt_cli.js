// Minimal launcher for the pxt-core CLI bundled with this project.
const path = require("path")

process.chdir(__dirname)

const cli = require(path.resolve("node_modules/pxt-core/built/pxt.js"))
const target = path.resolve("node_modules/pxt-microbit")
const keepAlive = setInterval(() => {}, 1000)

cli.mainCli(target, process.argv.slice(2))
    .catch(error => {
        console.error(error)
        process.exitCode = 1
    })
    .finally(() => clearInterval(keepAlive))
