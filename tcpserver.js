console.log("Made by JohNan - https://github.com/JohNan/pyflichub-tcpclient")

var net = require('net');
var buttons = require('buttons');

// Configuration - start
const PORT = 8124;
const EVENT_BUTTON = "button";
// Configuration - end

net.createServer(function (socket) {
    var refreshIntervalId = null;

    console.log("Connection from " + socket.remoteAddress);

    var buttonConnectedHandler = function (button) {
        console.log('Button connected:' + button.bdaddr)
        var response = {
            'event': 'buttonConnected',
            'button': button.bdaddr,
            'action': ''
        }
        socket.write(JSON.stringify(response))
    };


    var buttonReadyHandler = function (button) {
        console.log('Button ready:' + button.bdaddr)
        var response = {
            'event': 'buttonReady',
            'button': button.bdaddr,
            'action': ''
        }
        socket.write(JSON.stringify(response))
    };

    var buttonAddedHandler = function (button) {
        console.log('Button added:' + button.bdaddr)
        var response = {
            'event': 'buttonAdded',
            'button': button.bdaddr,
            'action': ''
        }
        socket.write(JSON.stringify(response))
    };

    var buttonDownHandler = function (button) {
        console.log('Button clicked:' + button.bdaddr + ' - down')
        var response = {
            'event': EVENT_BUTTON,
            'button': button.bdaddr,
            'action': 'down'
        }
        socket.write(JSON.stringify(response))
    };

    var buttonUpHandler = function (button) {
        console.log('Button clicked:' + button.bdaddr + ' - up')
        var response = {
            'event': EVENT_BUTTON,
            'button': button.bdaddr,
            'action': 'up'
        }
        socket.write(JSON.stringify(response))
    };

    var buttonSingleOrDoubleClickOrHoldHandler = function (button) {
        const action = button.isSingleClick ? 'single' : button.isDoubleClick ? 'double' : 'hold';
        console.log('Button clicked:' + button.bdaddr + ' - ' + action)
        const response = {
            'event': EVENT_BUTTON,
            'button': button.bdaddr,
            'action': action
        };
        socket.write(JSON.stringify(response))
    };

    function sendButtons() {
        const _buttons = buttons.getButtons();
        console.log(JSON.stringify(_buttons))

        const response = {
            'command': 'buttons',
            'data': _buttons
        };

        socket.write(JSON.stringify(response))
    }

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

        clearInterval(refreshIntervalId);
        socket.destroy();
    });

    socket.on('data', function (data) {
        const msg = data.trim()
        console.log("Received message: " + msg)

        if (msg.startsWith("battery;")) {
            const _bdaddr = msg.split(";")[1];
            const button = buttons.getButton(_bdaddr)

            const response = {
                'command': 'battery',
                'data': button.batteryStatus
            };

            socket.write(JSON.stringify(response))
        }

        if (msg === "buttons") {
            const _buttons = buttons.getButtons();
            console.log(JSON.stringify(_buttons))

            const response = {
                'command': 'buttons',
                'data': _buttons
            };

            socket.write(JSON.stringify(response))
        }

        if (msg === "ping") {
            socket.write("pong")
        }
    });

    // Send current buttons every 10 seconds
    refreshIntervalId = setInterval(sendButtons, 10000);
}).listen(PORT, function () {
    console.log("Opened server on port: " + PORT);
});

console.log("The server should have started now!")
console.log("Waiting for connections...")


