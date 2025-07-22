# Asynchronous Python TCP Client for FlicHub

Get events from the FlicHub when a Flic/Twist Button is clicked and send them to [home-assistant-flichub](https://github.com/JohNan/home-assistant-flichub).

To be able to use this client you need to enable the Flic Hub SDK described on [this](https://flic.io/flic-hub-sdk) page.

Create a new module and name it pyflichub-tcpclient (or any name) and paste the code found in `tcpserver.js` in the editor and press play. Check the box "Restart after crash or reboot."

This will open a TCP Server on port `8124` (configurable by changing `PORT`)

### Disclaimer
This python library was not made by Flic. It is not official, not developed, and not supported by Flic.
