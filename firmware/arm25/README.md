# Pro Micro arm firmware 2.5

Hardware-accepted source for the Classroom Studio mouse/sound arm.

- `ams_board25.ino` SHA-256: `4b54d04b328ea7a375daa82786fab733d9ae2055a21f6f72cc1a42164266c16c`
- UART brain link: 57600 baud, strict integrity framing after negotiation.
- Copy `ams_key.example.h` to `ams_key.h` and provision the project PSK locally. Never commit the real key or compiled image containing it.
