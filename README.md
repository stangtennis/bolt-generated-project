# Remote Desktop Application

A high-performance remote desktop application built with Python and WebSocket technology, allowing for secure and responsive remote desktop control through a web browser.

## Features

- Real-time screen sharing with optimized performance
- Secure WebSocket communication (WSS)
- Multi-level quality control system
  - Auto mode with smart quality adjustment
  - Manual quality settings (Low to Best)
- Performance monitoring
  - Real-time FPS counter
  - Bandwidth usage monitor
- Responsive mouse and keyboard control
- Modern, intuitive user interface
- Cross-platform compatibility
- Secure authentication system

## Performance Optimizations

- Double buffering with offscreen canvas
- Optimized JPEG compression
- Frame request throttling
- Smart quality auto-adjustment
- Efficient mouse event handling

## Security Features

- SSL/TLS encryption
- WebSocket Secure (WSS) protocol
- Input validation and sanitization
- Session-based authentication

## Requirements

- Python 3.8+
- Flask
- Flask-SocketIO
- Pillow (PIL)
- pywin32 (for Windows)
- Modern web browser with WebSocket support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/remote-desktop.git
cd remote-desktop
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
python web_server.py
```

4. Access the application:
Open your web browser and navigate to `https://localhost:5000`

## Usage

1. Start the server on the host machine
2. Connect from a client browser using the host's IP address
3. Select your preferred quality setting or use Auto mode
4. Monitor performance using the built-in FPS and bandwidth counters
5. Use your mouse and keyboard to control the remote desktop

## Configuration

The application can be configured through environment variables or config files:
- `PORT`: Server port (default: 5000)
- `HOST`: Host address (default: 0.0.0.0)
- `SSL_CERT`: Path to SSL certificate
- `SSL_KEY`: Path to SSL private key

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask team for the excellent web framework
- Socket.IO team for real-time communication capabilities
- All contributors who have helped improve this project
