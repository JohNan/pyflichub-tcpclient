console.log("Made by JohNan - https://github.com/JohNan/pyflichub-tcpclient")

const network = require('network');
const net = require('net');
const buttons = require('buttons');
const flicapp = require('flicapp');
const ir = require('ir');
const EOL = "\n";
const VERSION = "0.1.12";

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

    const sendButtonPayload = function (button, {event=EVENT_BUTTON, action='', button_number=undefined}) {
        const payload = {
            'event': event,
            'button': button.bdaddr,
            'action': action
        }
        if (button_number !== undefined) {
            payload['button_number'] = button_number;
        }
        write(payload)
    }

    const buttonConnectedHandler = function (obj) {
        console.log('Button connected:' + obj.bdaddr)
        sendButtonPayload({ bdaddr: obj.bdaddr }, {event: 'buttonConnected'})
    };

    const buttonReadyHandler = function (obj) {
        console.log('Button ready:' + obj.bdaddr)
        sendButtonPayload({ bdaddr: obj.bdaddr }, {event: 'buttonReady'})
    };

    const buttonAddedHandler = function (obj) {
        console.log('Button added:' + obj.button.bdaddr)
        sendButtonPayload({ bdaddr: obj.button.bdaddr }, {event: 'buttonAdded'})
    };

    const buttonDeletedHandler = function (obj) {
        console.log('Button deleted:' + obj.bdaddr)
        sendButtonPayload({ bdaddr: obj.bdaddr }, {event: 'buttonDeleted'})
    };

    const buttonDisconnectedHandler = function (obj) {
        console.log('Button disconnected:' + obj.bdaddr)
        sendButtonPayload({ bdaddr: obj.bdaddr }, {event: 'buttonDisconnected'})
    };

    const buttonDownHandler = function (obj) {
        console.log('Button clicked:' + obj.bdaddr + ' - down')
        sendButtonPayload({ bdaddr: obj.bdaddr }, {action: 'down', button_number: obj.buttonNumber})
    };

    const buttonUpHandler = function (obj) {
        console.log('Button clicked:' + obj.bdaddr + ' - up')
        sendButtonPayload({ bdaddr: obj.bdaddr }, {action: 'up', button_number: obj.buttonNumber})
    };
	
    const buttonIdle = function (obj) {
        console.log('Button ' + obj.bdaddr + ' returning to idle')
        sendButtonPayload({ bdaddr: obj.bdaddr }, {action: 'idle', button_number: obj.buttonNumber})
    }

    const buttonSingleOrDoubleClickOrHoldHandler = function (obj) {
        const action = obj.isSingleClick ? 'single' : obj.isDoubleClick ? 'double' : 'hold';
        console.log('Button clicked:' + obj.bdaddr + ' - ' + action)

        buttonDownHandler(obj);
        setTimeout(buttonUpHandler, 50, obj);
        setTimeout(sendButtonPayload, 100, { bdaddr: obj.bdaddr }, {action, button_number: obj.buttonNumber});
        setTimeout(buttonIdle, 150, obj);
    };

    const virtualDeviceUpdateHandler = function (metaData, values) {
        console.log('Twist ' + metaData.buttonId + ' updated virtual device ' + metaData.virtualDeviceId);
        const meta_data = {
            'button_id': metaData.buttonId,
            'virtual_device_id': metaData.virtualDeviceId,
            'dimmable_type': metaData.dimmableType
        };
        const payload = {
            'event': 'virtualDeviceUpdate',
            'meta_data': meta_data,
            'values': values
        };
        write(payload);
    };

    const actionMessageHandler = function (message) {
        console.log('Got an action message: ' + message);
        const payload = {
            'event': 'actionMessage',
            'action': message
        };
        write(payload);
    };

    buttons.on('buttonSingleOrDoubleClickOrHold', buttonSingleOrDoubleClickOrHoldHandler);
    buttons.on('buttonConnected', buttonConnectedHandler);
    buttons.on('buttonReady', buttonReadyHandler);
    buttons.on('buttonAdded', buttonAddedHandler);
    buttons.on('buttonDeleted', buttonDeletedHandler);
    buttons.on('buttonDisconnected', buttonDisconnectedHandler);

    flicapp.on('virtualDeviceUpdate', virtualDeviceUpdateHandler);
    flicapp.on('actionMessage', actionMessageHandler);

    socket.setEncoding("utf8");

    socket.on('end', function () {
        console.log('Client disconnected: ' + socket.remoteAddress);

        buttons.removeListener('buttonSingleOrDoubleClickOrHold', buttonSingleOrDoubleClickOrHoldHandler);
        buttons.removeListener('buttonConnected', buttonConnectedHandler);
        buttons.removeListener('buttonReady', buttonReadyHandler);
        buttons.removeListener('buttonAdded', buttonAddedHandler);
        buttons.removeListener('buttonDeleted', buttonDeletedHandler);
        buttons.removeListener('buttonDisconnected', buttonDisconnectedHandler);
        flicapp.removeListener('virtualDeviceUpdate', virtualDeviceUpdateHandler);
        flicapp.removeListener('actionMessage', actionMessageHandler);

        socket.destroy();
    });

    socket.on('data', function (data) {
        data.trim().split(EOL).forEach(function (msg) {
            console.log("Received message: " + msg)

            if (msg.startsWith("{")) {
                try {
                    const parsed = JSON.parse(msg);
                    if (parsed.command === "virtualDeviceUpdateState") {
                        flicapp.virtualDeviceUpdateState(parsed.dimmableType, parsed.virtualDeviceId, parsed.values);
                    }
                    const irCallback = function(error) {
                        if (error) {
                            console.log("IR Play Error: " + error);
                            write({'event': 'irResult', 'action': 'failed', 'meta_data': {'error': error.toString()}});
                        } else {
                            write({'event': 'irResult', 'action': 'success'});
                        }
                    };

                    if (parsed.command === "play_ir") {
                        ir.play(parsed.signal_id, irCallback);
                    }
                    if (parsed.command === "play_ir_raw") {
                        if (parsed.arr && Array.isArray(parsed.arr)) {
                            var timings = new Uint32Array(parsed.arr);
                            ir.play(timings, irCallback);
                        }
                    }
                } catch (e) {
                    console.error("Failed to parse JSON: " + msg);
                }
                return;
            }

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
