console.log("Made by JohNan - https://github.com/JohNan/pyflichub-tcpclient")

var net = require('net');
var buttons = require('buttons');

// Configuration - start
var PORT = 8123;
// Configuration - end

net.createServer(function (socket) {
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
            'event': 'buttonDown',
            'button': button.bdaddr,
            'action': 'down'
        }
        socket.write(JSON.stringify(response))
    };

    var buttonUpHandler = function (button) {
        console.log('Button clicked:' + button.bdaddr + ' - up')
        var response = {
            'event': 'buttonUp',
            'button': button.bdaddr,
            'action': 'up'
        }
        socket.write(JSON.stringify(response))
    };

    var buttonSingleOrDoubleClickOrHoldHandler = function (button) {
        var action = ''
        if (button.isSingleClick) action = 'single'
        if (button.isDoubleClick) action = 'double'
        if (button.isHold) action = 'hold'

        console.log('Button clicked:' + button.bdaddr + ' - ' + action)

        var response = {
            'event': 'buttonSingleOrDoubleClickOrHold',
            'button': button.bdaddr,
            'action': action
        }
        socket.write(JSON.stringify(response))
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

        buttons.removeListener('buttonUp', buttonUpHandler)
        buttons.removeListener('buttonDown', buttonDownHandler)
        buttons.removeListener('buttonSingleOrDoubleClickOrHold', buttonSingleOrDoubleClickOrHoldHandler)
        buttons.removeListener('buttonConnected', buttonConnectedHandler)
        buttons.removeListener('buttonReady', buttonReadyHandler)
        buttons.removeListener('buttonAdded', buttonAddedHandler)

        socket.destroy();
    });

    socket.on('data', function (data) {
        var msg = data.trim()
        console.log("Received message: " + msg)

        if (msg.startsWith("battery;")) {
            var _bdaddr = msg.split(";")[1];
            var button = buttons.getButton(_bdaddr)

            var response = {
                'command': 'battery',
                'data': button.batteryStatus
            }

            socket.write(JSON.stringify(response))
        }

        if (msg === "buttons") {
            var _buttons = buttons.getButtons()
            console.log(JSON.stringify(_buttons))

            var response = {
                'command': 'buttons',
                'data': _buttons
            }

            socket.write(JSON.stringify(response))
        }

        if (msg === "ping") {
            socket.write("pong")
        }
    });

}).listen(PORT, function () {
    console.log("Opened server on port: " + PORT);
});

console.log("The server should have started now!")
console.log("Waiting for connections...")


