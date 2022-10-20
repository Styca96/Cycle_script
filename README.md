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

## Command
For each line specify:
- Time: time to wait after the execution of the command. If the instrument is **sequence**, it represents the *number of repetitions* of the sequence
- Istrument: Object that is to perform the function. If is **sleep** wait only the time specified by *Time*
- Command: executable method of the selected instrument. If the instrument is **ARMxl**, it represents the *script* inside the root folder
- Argument: positional argument for the command. if no argument is needed enter **-**
