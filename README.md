# MACON TwinCAT ⇄ MongoDB Sync Tool

The MACON Sync Tool is a Python-based synchronization service that provides bidirectional live data exchange between a TwinCAT PLC (via ADS) and a MongoDB database. It supports live sync, manual push/pull operations, and an automated backup function.

This tool is part of the MACON software and is designed to keep PLC memory structures in sync with the database in real time, enabling full integration between machine-level control and higher-level data systems.

## Features

- Live synchronization between TwinCAT and MongoDB
- Push mode: send PLC data to MongoDB manually or on event
- Pull mode: load MongoDB data into the PLC
- Automatic backup of MongoDB data to local directory
- Support for complex data types including arrays, structs, strings, reals, and bools
- Optionally runs as a Windows Service for background operation
- Logging and diagnostics included

## Requirements

- Windows OS
- Python 3.10 or higher
- pyads
- pymongo
- MongoDB server (local or remote)
- TwinCAT 3 with ADS enabled and accessible (default port 851)

## Directory Structure

MACON_Sync/
├── macon_sync_core.py # Main synchronization logic
├── macon_sync_service.py # Windows service handler
├── macon_sync_tray.py # Optional tray interface
├── config.json # PLC and MongoDB configuration
├── logs/ # Log output directory
├── Export/ # Optional output folder for exports
├── Backups/ # Automatic backup storage
└── macon_logo.ico # Tray icon (optional)

## Installation

1. Clone or download this repository
2. Install dependencies:
pip install pyads pymongo

3. Edit the placeholders in the code to match your PLC NetId, ADS port, MongoDB connection string, and target collections.
4. Run the sync tool:
python macon_sync_core.py


To run as a Windows service or from the tray icon, see the corresponding scripts `macon_sync_service.py` and `macon_sync_tray.py`.

## PLC Integration

In TwinCAT, define the following:
- A global variable list or POU (e.g. `MACONDatabase`, `MachineDatabase`) with the data to be synced
- A structure like `ProductList` (array of structs) if syncing product metadata
- Control flags (e.g. `StartSync`, `BackupNow`, `PushToDatabase`, `PullFromDatabase`) if you want PLC-driven sync control

All PLC communication is handled via ADS using symbolic names.

## Backup Function

A backup is created in the `Backups/` folder, with a timestamped JSON dump of the relevant MongoDB collections. This can be triggered manually or automated via script or tray menu.

## Logging

All actions are logged in the `logs/` folder with timestamps. Log files are named by the date and operation.

## Notes

- Ensure TwinCAT is in RUN mode and ADS is accessible from the host machine
- MongoDB must be running before the sync tool starts
- Always test with mock data before enabling live sync in production

## License

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License.  
You may use, modify, and distribute the code for non-commercial purposes only.  
Full license text: [LICENSE.md](./LICENSE.md)


## Credits

Developed as part of the MACON Industrial Automation Platform. For more information, contact the developer.
