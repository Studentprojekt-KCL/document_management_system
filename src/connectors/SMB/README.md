# SMB Connector

Document management connector for SMB (Server Message Block) file shares and local file systems.

## Setup

To run this connector, you need a Python virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .
```

## Running

```bash
smb_connector
```

Set environment variables before running:
- `SMB_CONNECTOR_PORT` - Port for the API server
- `BASE_PATH` - Root path for file scanning
- `SKIP_DIRS` - Directories to skip (comma-separated)
- `ALLOWED_EXTENSIONS` - File extensions to include (comma-separated)
- `MAX_FILE_SIZE` - Maximum file size in bytes
