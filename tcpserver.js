console.log("Made by JohNan - https://github.com/JohNan/pyflichub-tcpclient")

const network = require('network');
const net = require('net');
const buttons = require('buttons');
const EOL = "\n";
const VERSION = "0.1.10";

// Configuration - start
const HOST = "0.0.0.0";
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
            'command': 'server',
            'data': {
                'version': VERSION
            }
        };

        write(payload)
    }

    console.log("Connection from " + socket.remoteAddress);

    const sendButtonPayload = function (button, {event=EVENT_BUTTON, action=''}) {
        const payload = {
            'event': event,
            'button': button.bdaddr,
            'action': action
        }
        write(payload)
    }

    const buttonConnectedHandler = function (button) {
        console.log('Button connected:' + button.bdaddr)
        sendButtonPayload(button, {event: 'buttonConnected'})
    };

    const buttonReadyHandler = function (button) {
        console.log('Button ready:' + button.bdaddr)
        sendButtonPayload(button, {event: 'buttonReady'})
    };

    const buttonAddedHandler = function (button) {
        console.log('Button added:' + button.bdaddr)
        sendButtonPayload(button, {event: 'buttonAdded'})
    };

    const buttonDownHandler = function (button) {
        console.log('Button clicked:' + button.bdaddr + ' - down')
        sendButtonPayload(button, {action: 'down'})
    };

    const buttonUpHandler = function (button) {
        console.log('Button clicked:' + button.bdaddr + ' - up')
        sendButtonPayload(button, {action: 'up'})
    };
	
    const buttonIdle = function (button) {
        console.log('Button ' + button.bdaddr + ' returning to idle')
        sendButtonPayload(button, {action: 'idle'})
    }

    const buttonSingleOrDoubleClickOrHoldHandler = function (button) {
        const action = button.isSingleClick ? 'single' : button.isDoubleClick ? 'double' : 'hold';
        console.log('Button clicked:' + button.bdaddr + ' - ' + action)
        sendButtonPayload(button, {action})
        // manually trigger a cycle so HA sees the button as newly "on"
        buttonDownHandler(button);
        buttonUpHandler(button);
        // set the button back to idle after a moment
        setTimeout(buttonIdle, 100, button);
    };

    buttons.on('buttonSingleOrDoubleClickOrHold', buttonSingleOrDoubleClickOrHoldHandler);
    buttons.on('buttonConnected', buttonConnectedHandler);
    buttons.on('buttonReady', buttonReadyHandler);
    buttons.on('buttonAdded', buttonAddedHandler);

    socket.setEncoding("utf8");

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
}).listen(PORT, HOST, function () {
    console.log("Opened server on port: " + PORT);
});

console.log("The server should have started now!")
console.log("Waiting for connections...")
