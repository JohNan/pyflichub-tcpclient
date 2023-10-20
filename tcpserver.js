console.log("Made by JohNan - https://github.com/JohNan/pyflichub-tcpclient")

const network = require('network');
const net = require('net');
const buttons = require('buttons');
const EOL = "\n";
const VERSION = "0.1.8";

// Configuration - start
const PORT = 8124;
const EVENT_BUTTON = "button";
// Configuration - end

net.createServer(function (socket) {
    function write(_payload) {
        socket.write(JSON.stringify(_payload) + EOL)
    }

    function sendButtons() {
        const _buttons = buttons.getButtons();
        console.log(JSON.stringify(_buttons))

        const payload = {
            'command': 'buttons',
            'data': _buttons
        };

        write(payload)
    }

    function sendNetworkInfo() {
        const _network = network.getState();
        console.log(JSON.stringify(_network))

        const payload = {
            'command': 'network',
            'data': _network
        };

        write(payload)
    }

    function sendServerInfo() {
        const payload = {
            'command': 'server_info',
            'data': {
                'version': VERSION
            }
        };

        write(payload)
    }

    console.log("Connection from " + socket.remoteAddress);

    const buttonConnectedHandler = function (button) {
        console.log('Button connected:' + button.bdaddr)
        const payload = {
            'event': 'buttonConnected',
            'button': button.bdaddr,
            'action': ''
        }
        write(payload)
    };


    const buttonReadyHandler = function (button) {
        console.log('Button ready:' + button.bdaddr)
        const payload = {
            'event': 'buttonReady',
            'button': button.bdaddr,
            'action': ''
        }
        write(payload)
    };

    const buttonAddedHandler = function (button) {
        console.log('Button added:' + button.bdaddr)
        const payload = {
            'event': 'buttonAdded',
            'button': button.bdaddr,
            'action': ''
        }
        write(payload)
    };

    const buttonDownHandler = function (button) {
        console.log('Button clicked:' + button.bdaddr + ' - down')
        const payload = {
            'event': EVENT_BUTTON,
            'button': button.bdaddr,
            'action': 'down'
        }
        write(payload)
    };

    const buttonUpHandler = function (button) {
        console.log('Button clicked:' + button.bdaddr + ' - up')
        const payload = {
            'event': EVENT_BUTTON,
            'button': button.bdaddr,
            'action': 'up'
        }
        write(payload)
    };

    const buttonSingleOrDoubleClickOrHoldHandler = function (button) {
        const action = button.isSingleClick ? 'single' : button.isDoubleClick ? 'double' : 'hold';
        console.log('Button clicked:' + button.bdaddr + ' - ' + action)
        const payload = {
            'event': EVENT_BUTTON,
            'button': button.bdaddr,
            'action': action
        };
        write(payload)
    };

    buttons.on('buttonSingleOrDoubleClickOrHold', buttonSingleOrDoubleClickOrHoldHandler);
    buttons.on('buttonUp', buttonUpHandler);
    buttons.on('buttonDown', buttonDownHandler);
    buttons.on('buttonConnected', buttonConnectedHandler);
    buttons.on('buttonReady', buttonReadyHandler);
    buttons.on('buttonAdded', buttonAddedHandler);

    socket.setEncoding();

    socket.on('end', function () {
        console.log('Client disconnected: ' + socket.remoteAddress);

        buttons.removeListener('buttonUp', buttonUpHandler);
        buttons.removeListener('buttonDown', buttonDownHandler);
        buttons.removeListener('buttonSingleOrDoubleClickOrHold', buttonSingleOrDoubleClickOrHoldHandler);
        buttons.removeListener('buttonConnected', buttonConnectedHandler);
        buttons.removeListener('buttonReady', buttonReadyHandler);
        buttons.removeListener('buttonAdded', buttonAddedHandler);

        socket.destroy();
    });

    socket.on('data', function (data) {
        data.trim().split(EOL).forEach(function (msg) {
            console.log("Received message: " + msg)

            switch (msg) {
                case "buttons":
                    sendButtons();
                    break;
                case "network":
                    sendNetworkInfo();
                    break;
                case "server":
                    sendServerInfo();
                    break;
                case "ping":
                    write("pong")
                    break;
                default:
                    console.error("Unknown command: " + msg)
            }
        });
    });
}).listen(PORT, function () {
    console.log("Opened server on port: " + PORT);
});

console.log("The server should have started now!")
console.log("Waiting for connections...")