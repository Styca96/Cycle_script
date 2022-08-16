# SEQUENCE COMMAND REPOSITORY

Multiple script for execute test with sequential command.
Contain:

- **cycle script.py**: main script for execute test with sequential command
- **cycle_graphics.py**: graphic review of command for sequential test
- **create_sequence_from_excel.py**: create new user define sequence

## Cycle_script

Script for execute sequential command on multiple Instrument:

Can command:

- Climate Chamber (modbus protocol)
  - ACS Discovery
- DC Source (SCPI protocol)
  - ITECH dc bidiretional load
- AC Source (SCPI protocol)
  - CHROMA grid simulator
- Power Supply (SCPI protocol)
  - HP6032A
- Oscilloscope (SCPI protocol):
  - MSO58B
- ARMxl (SSH protocol)
- User define sequence (Sequence)

# CLONE REPOSITORY

* Open Git Bash and run:

```
git clone https://github.com/Styca96/Cycle_script.git --branch working
```
